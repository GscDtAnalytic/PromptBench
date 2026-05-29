"""
Seed end-to-end.

Cria:
- 2 Tasks (resume_matching, support)
- 60 TestCases (30 por task, dos JSONLs)
- 10 PromptVersions (5 por task, dos YAMLs)
- 2 ModelConfigs fake (fake-fast, fake-thorough)
- 4 EvalRuns demo: (v1 baseline, v3 fewshot) × 2 tasks, rodando INLINE
  (sem precisar do worker arq) — produz Scorecards + caso de regressão visível.

Idempotente: detecta o que já existe pelo slug/version_number e pula.

Uso (dentro do container backend):
    python -m scripts.seed
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select

from app.core.db import session_scope
from app.evaluation.regression import compare_runs
from app.models import EvalRun, ModelConfig, PromptVersion, Scorecard, Task, TestCase
from app.models.enums import Provider, SliceLabel, TaskType
from app.workers.tasks import _execute_run

# Paths — funcionam tanto no docker (volumes /datasets, /prompts) quanto local
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATASETS_DIR = Path("/datasets") if Path("/datasets").exists() else REPO_ROOT / "datasets"
PROMPTS_DIR = Path("/prompts") if Path("/prompts").exists() else REPO_ROOT / "prompts"


TASK_DEFS = [
    {
        "name": "Resume × Job Matching",
        "slug": "task_a_resume_matching",
        "description": "Extração estruturada: match_score, matched_skills, missing_skills.",
        "task_type": TaskType.structured_extraction,
        "dataset_file": "task_a_resume_matching.jsonl",
        "prompts_dir": "task_a",
    },
    {
        "name": "Atendimento — Classificação e Resposta",
        "slug": "task_b_support",
        "description": "Classifica mensagem (category, priority) e sugere resposta.",
        "task_type": TaskType.classification_response,
        "dataset_file": "task_b_support.jsonl",
        "prompts_dir": "task_b",
    },
]

MODEL_CONFIGS = [
    # --- Fake (default do MVP): os runs de demo rodam aqui, sem chave de API ---
    {
        "provider": Provider.fake,
        "model_name": "fake-fast",
        "temperature": 0.0,
        "max_tokens": 800,
        "price_per_1m_input": 0.30,
        "price_per_1m_output": 1.00,
    },
    {
        "provider": Provider.fake,
        "model_name": "fake-thorough",
        "temperature": 0.0,
        "max_tokens": 1500,
        "price_per_1m_input": 3.00,
        "price_per_1m_output": 15.00,
    },
    # --- Reais: entram no catálogo (linhas no banco, custo zero) para ficarem
    # selecionáveis na UI. NÃO são exercitados pelo `make seed` — chamada real só
    # via `make smoke` / `make run.real` (opt-in, exige chave no .env).
    # Pricing em USD/1M tokens, conferido em maio/2026 (ver docs/ADR.md / README).
    {
        "provider": Provider.claude,
        "model_name": "claude-haiku-4-5",
        "temperature": 0.0,
        "max_tokens": 1024,
        "price_per_1m_input": 1.00,
        "price_per_1m_output": 5.00,
    },
    {
        "provider": Provider.claude,
        "model_name": "claude-sonnet-4-6",
        "temperature": 0.0,
        "max_tokens": 1500,
        "price_per_1m_input": 3.00,
        "price_per_1m_output": 15.00,
    },
    {
        "provider": Provider.openai,
        "model_name": "gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 1024,
        "price_per_1m_input": 0.15,
        "price_per_1m_output": 0.60,
    },
    {
        "provider": Provider.openai,
        "model_name": "gpt-4.1-mini",
        "temperature": 0.0,
        "max_tokens": 1500,
        "price_per_1m_input": 0.40,
        "price_per_1m_output": 1.60,
    },
]


async def _upsert_tasks(session: Any) -> dict[str, Task]:
    out: dict[str, Task] = {}
    for td in TASK_DEFS:
        result = await session.execute(select(Task).where(Task.slug == td["slug"]))
        task = result.scalar_one_or_none()
        if task is None:
            task = Task(
                name=td["name"],
                slug=td["slug"],
                description=td["description"],
                task_type=td["task_type"],
            )
            session.add(task)
            await session.flush()
            print(f"  + Task '{td['slug']}' criada (id={task.id})")
        else:
            print(f"  = Task '{td['slug']}' já existe (id={task.id})")
        out[td["slug"]] = task
    return out


async def _upsert_testcases(session: Any, task: Task, dataset_file: str) -> int:
    existing = await session.scalar(
        select(TestCase).where(TestCase.task_id == task.id).limit(1)
    )
    if existing is not None:
        print(f"  = TestCases de '{task.slug}' já existem — pulando")
        return 0

    path = DATASETS_DIR / dataset_file
    count = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            tc = TestCase(
                task_id=task.id,
                input=row["input"],
                expected=row.get("expected"),
                slice=SliceLabel(row["slice"]),
                rubric_notes=row.get("rubric_notes"),
            )
            session.add(tc)
            count += 1
    await session.flush()
    print(f"  + {count} TestCases carregados em '{task.slug}'")
    return count


async def _upsert_prompts(session: Any, task: Task, prompts_subdir: str) -> dict[str, PromptVersion]:
    out: dict[str, PromptVersion] = {}
    dir_path = PROMPTS_DIR / prompts_subdir
    files = sorted(dir_path.glob("v*.yaml"))
    for i, yaml_path in enumerate(files, start=1):
        with yaml_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        result = await session.execute(
            select(PromptVersion).where(
                PromptVersion.task_id == task.id,
                PromptVersion.version_number == i,
            )
        )
        pv = result.scalar_one_or_none()
        if pv is None:
            pv = PromptVersion(
                task_id=task.id,
                version_number=i,
                name=data["name"],
                system_prompt=data["system_prompt"],
                user_template=data["user_template"],
                model_params=data.get("model_params", {}),
                is_baseline=bool(data.get("is_baseline", False)),
            )
            session.add(pv)
            await session.flush()
            print(f"  + PromptVersion '{task.slug}'/v{i}_{data['name']} criada")
        else:
            print(f"  = PromptVersion '{task.slug}'/v{i} já existe")
        out[data["name"]] = pv
    return out


async def _upsert_model_configs(session: Any) -> dict[str, ModelConfig]:
    out: dict[str, ModelConfig] = {}
    for mc_def in MODEL_CONFIGS:
        result = await session.execute(
            select(ModelConfig).where(
                ModelConfig.provider == mc_def["provider"],
                ModelConfig.model_name == mc_def["model_name"],
            )
        )
        mc = result.scalar_one_or_none()
        if mc is None:
            mc = ModelConfig(**mc_def)
            session.add(mc)
            await session.flush()
            print(f"  + ModelConfig {mc_def['provider'].value}/{mc_def['model_name']} criada")
        else:
            print(
                f"  = ModelConfig {mc_def['provider'].value}/{mc_def['model_name']} já existe"
            )
        out[mc_def["model_name"]] = mc
    return out


async def _existing_run(
    session: Any, task_id: int, prompt_version_id: int, model_config_id: int
) -> EvalRun | None:
    result = await session.execute(
        select(EvalRun).where(
            EvalRun.task_id == task_id,
            EvalRun.prompt_version_id == prompt_version_id,
            EvalRun.model_config_id == model_config_id,
        )
    )
    return result.scalar_one_or_none()


async def _seed_demo_run(
    session: Any,
    task: Task,
    prompt: PromptVersion,
    model_config: ModelConfig,
) -> EvalRun:
    existing = await _existing_run(session, task.id, prompt.id, model_config.id)
    if existing is not None:
        existing_sc = (
            await session.execute(
                select(Scorecard).where(Scorecard.eval_run_id == existing.id)
            )
        ).scalar_one_or_none()
        if existing_sc is not None:
            print(
                f"    = EvalRun {prompt.name} já tem scorecard (run #{existing.id}) — pulando"
            )
            return existing
    if existing is None:
        existing = EvalRun(
            task_id=task.id,
            prompt_version_id=prompt.id,
            model_config_id=model_config.id,
            repetitions=3,
        )
        session.add(existing)
        await session.flush()
        print(f"    + Criado EvalRun #{existing.id} para {prompt.name}")
    print(f"    > Executando EvalRun #{existing.id}...")
    await _execute_run(session, existing.id)
    print(f"    ✓ EvalRun #{existing.id} concluído")
    return existing


async def main() -> int:
    print("== PromptBench seed ==\n")
    print(f"datasets dir: {DATASETS_DIR}")
    print(f"prompts dir:  {PROMPTS_DIR}\n")

    async with session_scope() as session:
        print("[1/4] Tasks")
        tasks_by_slug = await _upsert_tasks(session)

        print("\n[2/4] TestCases + Prompts")
        prompts_by_slug: dict[str, dict[str, PromptVersion]] = {}
        for td in TASK_DEFS:
            t = tasks_by_slug[td["slug"]]
            await _upsert_testcases(session, t, td["dataset_file"])
            prompts_by_slug[td["slug"]] = await _upsert_prompts(session, t, td["prompts_dir"])

        print("\n[3/4] ModelConfigs")
        mcs = await _upsert_model_configs(session)

        print(
            "\n[4/4] EvalRuns de demonstração (v1_baseline × v3_fewshot) × (fake-fast × fake-thorough)"
        )
        # demo_runs[slug][prompt_key][model_name] = EvalRun
        demo_runs: dict[str, dict[str, dict[str, EvalRun]]] = {}
        prompt_keys = ["v1_baseline", "v3_fewshot"]
        model_keys = ["fake-fast", "fake-thorough"]
        for td in TASK_DEFS:
            task = tasks_by_slug[td["slug"]]
            prompts = prompts_by_slug[td["slug"]]
            print(f"\n  Task '{task.slug}':")
            per_prompt: dict[str, dict[str, EvalRun]] = {}
            for pk in prompt_keys:
                per_model: dict[str, EvalRun] = {}
                for mk in model_keys:
                    run = await _seed_demo_run(session, task, prompts[pk], mcs[mk])
                    per_model[mk] = run
                per_prompt[pk] = per_model
            demo_runs[td["slug"]] = per_prompt

        async def _sc(run_id: int) -> Scorecard | None:
            return (
                await session.execute(
                    select(Scorecard).where(Scorecard.eval_run_id == run_id)
                )
            ).scalar_one_or_none()

        # Veredito do caso-âncora (v1 vs v3, no fake-fast)
        print("\n== Veredito do caso-âncora: compare(v1_baseline, v3_fewshot) em fake-fast ==")
        for slug, per_prompt in demo_runs.items():
            sc_v1 = await _sc(per_prompt["v1_baseline"]["fake-fast"].id)
            sc_v3 = await _sc(per_prompt["v3_fewshot"]["fake-fast"].id)
            if sc_v1 is None or sc_v3 is None:
                print(f"  {slug}: scorecard ausente — pulando veredito")
                continue
            verdict = compare_runs(baseline=sc_v1, candidate=sc_v3)
            print(f"\n  {slug}:")
            print(f"    v1 aggregate={sc_v1.aggregate_score:.3f}  v3={sc_v3.aggregate_score:.3f}")
            print(f"    veredito: {'APROVADO' if verdict.passed else 'REPROVADO'}")
            if verdict.failures:
                for f in verdict.failures:
                    print(f"      - {f}")

        # Comparação cross-model: mesmo prompt (v3), modelo diferente
        print("\n== Comparação cross-model: compare(fake-fast, fake-thorough) em v3_fewshot ==")
        for slug, per_prompt in demo_runs.items():
            sc_fast = await _sc(per_prompt["v3_fewshot"]["fake-fast"].id)
            sc_thorough = await _sc(per_prompt["v3_fewshot"]["fake-thorough"].id)
            if sc_fast is None or sc_thorough is None:
                print(f"  {slug}: scorecard ausente — pulando")
                continue
            cost_pct = (
                (sc_thorough.total_cost_usd - sc_fast.total_cost_usd) / sc_fast.total_cost_usd
                if sc_fast.total_cost_usd
                else 0.0
            )
            print(f"\n  {slug}:")
            print(
                f"    fake-fast      score={sc_fast.aggregate_score:.3f}  "
                f"lat={sc_fast.avg_latency_ms:.0f}ms  cost=${sc_fast.total_cost_usd:.6f}"
            )
            print(
                f"    fake-thorough  score={sc_thorough.aggregate_score:.3f}  "
                f"lat={sc_thorough.avg_latency_ms:.0f}ms  cost=${sc_thorough.total_cost_usd:.6f}"
            )
            print(f"    cost Δ = {cost_pct:+.1%}")

        print("\n== Seed concluído ==")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
