"""
SQLAlchemy models — fonte da verdade do schema.

REGRA DE OURO 1 (CLAUDE.md): PromptVersion é IMUTÁVEL. Não há UPDATE em prompt_versions.
"Editar" = criar nova versão com version_number incrementado.
"""

from app.models.enums import Provider, RunStatus, SliceLabel, TaskType
from app.models.eval_result import EvalResult
from app.models.eval_run import EvalRun
from app.models.model_config import ModelConfig
from app.models.prompt_version import PromptVersion
from app.models.scorecard import Scorecard
from app.models.task import Task
from app.models.test_case import TestCase

__all__ = [
    "EvalResult",
    "EvalRun",
    "ModelConfig",
    "PromptVersion",
    "Provider",
    "RunStatus",
    "Scorecard",
    "SliceLabel",
    "Task",
    "TaskType",
    "TestCase",
]
