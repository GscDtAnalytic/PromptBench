"""
Worker arq. Executa EvalRuns enfileirados pela API.

Cada job: itera (test_case × repetition), chama o adapter, roda checks
determinísticos, roda o RubricJudge, persiste EvalResult, e ao final agrega o Scorecard.

Falhas de provedor viram EvalResult.error e NÃO derrubam o lote (CLAUDE.md §7).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

import structlog
from arq.connections import RedisSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters import get_adapter
from app.core.config import get_settings
from app.core.db import session_scope
from app.core.logging import configure_logging
from app.core.pricing import compute_cost_usd
from app.evaluation.aggregate import EvalResultRecord, aggregate
from app.evaluation.checks import run_checks
from app.evaluation.judge import RubricInputs, RubricJudge, RubricOutputs
from app.evaluation.render import render_template
from app.evaluation.task_checks import (
    checks_for,
    rubric_criteria,
    task_description,
)
from app.models import EvalResult, EvalRun, Scorecard
from app.models.enums import Provider, RunStatus, SliceLabel, TaskType

log = structlog.get_logger("worker")


async def _run_one(
    *,
    session: AsyncSession,
    run: EvalRun,
    task_type: TaskType,
    task_slug: str,
    test_case_id: int,
    test_case_input: dict[str, Any],
    test_case_expected: dict[str, Any] | None,
    test_case_slice: SliceLabel,
    repetition_index: int,
    prompt_version_name: str,
    system_prompt: str,
    user_template: str,
    model_params: dict[str, Any],
    price_per_1m_input: float,
    price_per_1m_output: float,
) -> EvalResult:
    """Roda um único (test_case × repetição) e retorna o EvalResult persistido."""

    user_rendered = render_template(user_template, test_case_input)
    params = {
        **model_params,
        "_scenario_hint": {
            "task_slug": task_slug,
            "prompt_version_name": prompt_version_name,
            "slice": test_case_slice.value,
            "input": test_case_input,
            "expected": test_case_expected,
            "repetition_index": repetition_index,
        },
    }

    adapter = get_adapter(run.model_config.provider, run.model_config.model_name)

    raw_output: str | None = None
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    error: str | None = None

    try:
        response = await adapter.call(system=system_prompt, user=user_rendered, params=params)
        raw_output = response.text
        latency_ms = response.latency_ms
        input_tokens = response.input_tokens
        output_tokens = response.output_tokens
        cost_usd = compute_cost_usd(
            input_tokens, output_tokens, price_per_1m_input, price_per_1m_output
        )
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        log.error("worker.adapter_error", run_id=run.id, error=error)

    # checks determinísticos (só se houver output)
    deterministic_scores: dict[str, dict[str, Any]] = {}
    all_required_passed = True
    if raw_output is not None and test_case_expected is not None:
        specs = checks_for(task_type, test_case_slice)
        results = run_checks(specs, raw_output, test_case_expected)
        for name, cr in results.items():
            deterministic_scores[name] = {
                "passed": cr.passed,
                "score": cr.score,
                "detail": cr.detail,
            }
            spec = next((s for s in specs if s.name == name), None)
            if spec and spec.required and not cr.passed:
                all_required_passed = False
    elif raw_output is not None:
        # sem expected: roda só checks que não dependem de expected
        specs = [s for s in checks_for(task_type, test_case_slice) if s.name in {"json_schema_valid", "required_fields_present"}]
        results = run_checks(specs, raw_output, {})
        for name, cr in results.items():
            deterministic_scores[name] = {
                "passed": cr.passed,
                "score": cr.score,
                "detail": cr.detail,
            }
            if cr.passed is False:
                all_required_passed = False

    # rubric judge (só se houver output e checks determinísticos não falharam catastrofic.)
    rubric_scores: dict[str, Any] = {}
    if raw_output is not None and all_required_passed:
        # Judge fixo se configurado (anti-viés), senão usa o modelo do próprio run.
        settings = get_settings()
        if settings.judge_provider is not None and settings.judge_model is not None:
            judge_adapter = get_adapter(
                Provider(settings.judge_provider), settings.judge_model
            )
        else:
            judge_adapter = get_adapter(
                run.model_config.provider, run.model_config.model_name
            )
        judge = RubricJudge(adapter=judge_adapter)
        rubric_inputs = RubricInputs(
            task_description=task_description(task_type),
            test_case_input=test_case_input,
            candidate_output=raw_output,
            rubric_criteria=rubric_criteria(task_type),
        )
        try:
            verdict = await judge.judge(rubric_inputs)
        except Exception as e:
            rubric_scores = {"judge_error": f"{type(e).__name__}: {e}"}
        else:
            if isinstance(verdict, RubricOutputs):
                rubric_scores = {
                    "quality": verdict.quality,
                    "instruction_adherence": verdict.instruction_adherence,
                    "factual_structural": verdict.factual_structural,
                    "tone_format": verdict.tone_format,
                    "reasoning": verdict.reasoning,
                }
            else:
                rubric_scores = {"judge_error": verdict.judge_error}
    elif raw_output is None:
        # falha de adapter: marca rubric com judge_error explícito
        rubric_scores = {"judge_error": "no_output"}
    else:
        # checks determinísticos falharam: ainda assim quero ter um sinal — mas não invoca judge
        # para economizar tokens. O aggregate trata passed=False como score 0.
        rubric_scores = {"judge_error": "skipped_due_to_failed_required_check"}

    passed = (
        error is None and all_required_passed and "judge_error" not in rubric_scores
    )

    eval_result = EvalResult(
        eval_run_id=run.id,
        test_case_id=test_case_id,
        repetition_index=repetition_index,
        raw_output=raw_output,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        deterministic_scores=deterministic_scores or None,
        rubric_scores=rubric_scores or None,
        passed=passed,
        error=error,
    )
    session.add(eval_result)
    return eval_result


async def _execute_run(
    session: AsyncSession, run_id: int, *, max_cases: int | None = None
) -> None:
    # carrega tudo que precisamos com selectinload
    stmt = (
        select(EvalRun)
        .options(
            selectinload(EvalRun.task).selectinload(__import__("app.models", fromlist=["Task"]).Task.test_cases),
            selectinload(EvalRun.prompt_version),
            selectinload(EvalRun.model_config),
        )
        .where(EvalRun.id == run_id)
    )
    result = await session.execute(stmt)
    run = result.scalar_one_or_none()
    if run is None:
        log.error("worker.run_not_found", run_id=run_id)
        return

    run.status = RunStatus.running
    await session.flush()
    # Commit imediato: o GET /runs/{id}/status roda em OUTRA sessão e só enxerga
    # linhas commitadas. Sem isso, a UI veria "pending" até o run inteiro acabar.
    await session.commit()

    test_cases = list(run.task.test_cases)
    if max_cases is not None:
        # Apenas para runs reais controlados (cost cap). O worker arq nunca passa isso.
        test_cases = test_cases[:max_cases]
    log.info("worker.start", run_id=run_id, n_cases=len(test_cases), reps=run.repetitions)

    records: list[EvalResultRecord] = []
    for tc in test_cases:
        for rep in range(run.repetitions):
            er = await _run_one(
                session=session,
                run=run,
                task_type=run.task.task_type,
                task_slug=run.task.slug,
                test_case_id=tc.id,
                test_case_input=tc.input,
                test_case_expected=tc.expected,
                test_case_slice=tc.slice,
                repetition_index=rep,
                prompt_version_name=run.prompt_version.name,
                system_prompt=run.prompt_version.system_prompt,
                user_template=run.prompt_version.user_template,
                model_params=run.prompt_version.model_params,
                price_per_1m_input=run.model_config.price_per_1m_input,
                price_per_1m_output=run.model_config.price_per_1m_output,
            )
            await session.flush()
            records.append(
                EvalResultRecord(
                    test_case_id=tc.id,
                    slice=tc.slice,
                    repetition_index=rep,
                    passed=er.passed,
                    deterministic_scores=er.deterministic_scores or {},
                    rubric_scores=er.rubric_scores or {},
                    latency_ms=er.latency_ms,
                    cost_usd=er.cost_usd,
                )
            )
            # Commit incremental: cada EvalResult fica visível ao endpoint de status,
            # alimentando a barra de progresso em tempo real. expire_on_commit=False
            # mantém run.task/prompt_version/model_config carregados entre iterações.
            await session.commit()

    payload = aggregate(records, run.task.task_type)
    scorecard = Scorecard(
        eval_run_id=run.id,
        aggregate_score=payload.aggregate_score,
        quality=payload.quality,
        instruction_adherence=payload.instruction_adherence,
        factual_structural=payload.factual_structural,
        tone_format=payload.tone_format,
        avg_latency_ms=payload.avg_latency_ms,
        total_cost_usd=payload.total_cost_usd,
        failure_rate=payload.failure_rate,
        variance=payload.variance,
        per_slice_breakdown=payload.per_slice_breakdown,
    )
    session.add(scorecard)
    run.status = RunStatus.done
    run.finished_at = datetime.utcnow()
    await session.flush()
    log.info("worker.done", run_id=run_id, aggregate=payload.aggregate_score)


async def run_eval_run(ctx: dict[str, Any], run_id: int) -> dict[str, Any]:
    """Entry point chamado pelo arq."""
    async with session_scope() as session:
        try:
            await _execute_run(session, run_id)
        except Exception:
            log.exception("worker.failed", run_id=run_id)
            # A transação atual pode estar suja pela exceção: rollback antes de
            # persistir o status. Commit explícito porque o `raise` abaixo faria o
            # session_scope reverter o `failed` (deixando o run preso em "running").
            await session.rollback()
            run = await session.get(EvalRun, run_id)
            if run is not None:
                run.status = RunStatus.failed
                run.finished_at = datetime.utcnow()
                await session.commit()
            raise
    return {"run_id": run_id, "ok": True}


async def startup(ctx: dict[str, Any]) -> None:
    configure_logging()
    log.info("worker.startup")


async def shutdown(ctx: dict[str, Any]) -> None:
    log.info("worker.shutdown")


class WorkerSettings:
    """Configuração do worker arq (lido pelo CLI `arq app.workers.tasks.WorkerSettings`)."""

    functions: ClassVar = [run_eval_run]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs: ClassVar[int] = 4
    # Um EvalRun real roda o dataset inteiro × repetições contra a API (candidato +
    # judge). 90 resultados × latência real estoura fácil o default de 300s do arq,
    # que mataria o job no meio. 2h dá folga; o commit incremental garante que, mesmo
    # se estourar, o progresso parcial fica salvo.
    job_timeout: ClassVar[int] = 7200
    # Não re-tentar o job inteiro em caso de falha (evita duplicar EvalResults, já que
    # _execute_run não é idempotente por resultado). Falhas de provedor já são tratadas
    # por-chamada dentro de _run_one.
    max_tries: ClassVar[int] = 1
    redis_settings: ClassVar = RedisSettings.from_dsn(get_settings().redis_url)
