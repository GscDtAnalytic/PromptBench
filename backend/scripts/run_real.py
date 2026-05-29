"""
Roda UM EvalRun real end-to-end pelo MESMO caminho do worker (`_execute_run`).

Cria um EvalRun (task × prompt × model_config reais), executa com um cost cap
opcional (`--max-cases`) e imprime o Scorecard resultante — incluindo o breakdown
por slice. Usa o pipeline de verdade: adapter real → checks → RubricJudge → agregação.

Pré-requisitos:
- `.env` com a chave do provider escolhido.
- `make seed` já rodado (Tasks/Prompts/ModelConfigs reais existem no banco).

Uso (dentro do container backend, ou venv local + .env):
    python -m scripts.run_real                      # defaults baratos (Claude haiku, 3 casos)
    python -m scripts.run_real --provider openai --model gpt-4o-mini
    python -m scripts.run_real --task task_b_support --prompt-version 4 --reps 3 --max-cases 5

Controle de custo: chamadas ≈ max_cases × reps × (1 candidato + até 1 judge).
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import select

from app.core.db import session_scope
from app.models import EvalRun, ModelConfig, PromptVersion, Scorecard, Task
from app.models.enums import Provider
from app.workers.tasks import _execute_run


async def _resolve(session, task_slug, version_number, provider, model_name):
    task = (
        await session.execute(select(Task).where(Task.slug == task_slug))
    ).scalar_one_or_none()
    if task is None:
        raise SystemExit(f"Task '{task_slug}' não encontrada. Rode `make seed` antes.")

    pv = (
        await session.execute(
            select(PromptVersion).where(
                PromptVersion.task_id == task.id,
                PromptVersion.version_number == version_number,
            )
        )
    ).scalar_one_or_none()
    if pv is None:
        raise SystemExit(
            f"PromptVersion v{version_number} de '{task_slug}' não encontrada."
        )

    mc = (
        await session.execute(
            select(ModelConfig).where(
                ModelConfig.provider == provider,
                ModelConfig.model_name == model_name,
            )
        )
    ).scalar_one_or_none()
    if mc is None:
        raise SystemExit(
            f"ModelConfig {provider.value}/{model_name} não existe. "
            "Adicione ao seed (MODEL_CONFIGS) e rode `make seed`."
        )
    return task, pv, mc


async def main() -> int:
    parser = argparse.ArgumentParser(description="EvalRun real end-to-end")
    parser.add_argument("--task", default="task_a_resume_matching")
    parser.add_argument("--prompt-version", type=int, default=4, dest="version")
    parser.add_argument(
        "--provider",
        default="claude",
        choices=[p.value for p in Provider if p != Provider.fake],
    )
    parser.add_argument("--model", default="claude-haiku-4-5", dest="model_name")
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument(
        "--max-cases",
        type=int,
        default=3,
        help="Cost cap: nº de test cases (default 3). Use 0 para rodar TODOS.",
    )
    args = parser.parse_args()
    provider = Provider(args.provider)
    max_cases = None if args.max_cases == 0 else args.max_cases

    async with session_scope() as session:
        task, pv, mc = await _resolve(
            session, args.task, args.version, provider, args.model_name
        )

        run = EvalRun(
            task_id=task.id,
            prompt_version_id=pv.id,
            model_config_id=mc.id,
            repetitions=args.reps,
        )
        session.add(run)
        await session.flush()

        print("== EvalRun REAL ==")
        print(f"  task      : {task.slug}")
        print(f"  prompt    : v{pv.version_number}_{pv.name}")
        print(f"  model     : {provider.value}/{mc.model_name}")
        print(f"  reps      : {args.reps}   max_cases: {max_cases or 'TODOS'}")
        print(f"  run id    : #{run.id}\n  executando...\n")

        await _execute_run(session, run.id, max_cases=max_cases)

        sc = (
            await session.execute(
                select(Scorecard).where(Scorecard.eval_run_id == run.id)
            )
        ).scalar_one_or_none()
        if sc is None:
            print("✗ Nenhum scorecard gerado (run pode ter falhado). Veja os logs.")
            return 1

        print("== Scorecard ==")
        print(f"  aggregate_score      : {sc.aggregate_score:.3f}")
        print(f"  quality              : {sc.quality:.3f}")
        print(f"  instruction_adherence: {sc.instruction_adherence:.3f}")
        print(f"  factual_structural   : {sc.factual_structural:.3f}")
        print(f"  tone_format          : {sc.tone_format:.3f}")
        print(f"  avg_latency_ms       : {sc.avg_latency_ms:.0f}")
        print(f"  total_cost_usd       : ${sc.total_cost_usd:.6f}")
        print(f"  failure_rate         : {sc.failure_rate:.1%}")
        print(f"  variance             : {sc.variance:.4f}")
        print("  per_slice_breakdown  :")
        for slice_name, data in (sc.per_slice_breakdown or {}).items():
            print(f"    - {slice_name}: {data}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
