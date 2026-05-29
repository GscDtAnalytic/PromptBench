"""
Smoke test do bloco 2:
- Todos os models importam sem erro (sem ciclo)
- Base.metadata tem as 7 tabelas esperadas
- Os relacionamentos resolvem (mapper configura)
"""

from __future__ import annotations

from sqlalchemy.orm import configure_mappers

from app.core.db import Base
from app.models import (
    EvalResult,
    EvalRun,
    ModelConfig,
    PromptVersion,
    Scorecard,
    Task,
    TestCase,
)

EXPECTED_TABLES = {
    "tasks",
    "prompt_versions",
    "test_cases",
    "model_configs",
    "eval_runs",
    "eval_results",
    "scorecards",
}


def test_all_seven_tables_registered() -> None:
    names = set(Base.metadata.tables.keys())
    assert EXPECTED_TABLES.issubset(names), f"faltando: {EXPECTED_TABLES - names}"


def test_mappers_configure() -> None:
    """Falha se algum relationship apontar para classe inexistente / typo."""
    configure_mappers()


def test_prompt_version_unique_constraint() -> None:
    table = PromptVersion.__table__
    constraint_names = {c.name for c in table.constraints}
    assert "uq_prompt_task_version" in constraint_names


def test_scorecard_one_to_one_with_evalrun() -> None:
    col = Scorecard.__table__.c.eval_run_id
    assert col.unique is True


def test_cascade_delete_task_to_promptversions() -> None:
    fk = next(iter(PromptVersion.__table__.c.task_id.foreign_keys))
    assert fk.ondelete == "CASCADE"


def test_cascade_delete_evalrun_to_evalresults() -> None:
    fk = next(iter(EvalResult.__table__.c.eval_run_id.foreign_keys))
    assert fk.ondelete == "CASCADE"


def test_model_classes_exposed() -> None:
    # type-check de import: garante __init__ exporta tudo
    assert Task and PromptVersion and TestCase and ModelConfig
    assert EvalRun and EvalResult and Scorecard
