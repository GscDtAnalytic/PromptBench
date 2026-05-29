from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import RunStatus

if TYPE_CHECKING:
    from app.models.eval_result import EvalResult
    from app.models.model_config import ModelConfig
    from app.models.prompt_version import PromptVersion
    from app.models.scorecard import Scorecard
    from app.models.task import Task


class EvalRun(Base):
    __tablename__ = "eval_runs"
    __table_args__ = (
        Index("ix_evalrun_task_status", "task_id", "status"),
        Index("ix_evalrun_promptversion", "prompt_version_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    prompt_version_id: Mapped[int] = mapped_column(
        ForeignKey("prompt_versions.id", ondelete="CASCADE"), nullable=False
    )
    model_config_id: Mapped[int] = mapped_column(
        ForeignKey("model_configs.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[RunStatus] = mapped_column(
        SAEnum(RunStatus, name="run_status"), nullable=False, default=RunStatus.pending
    )
    repetitions: Mapped[int] = mapped_column(nullable=False, default=3)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)

    task: Mapped[Task] = relationship(back_populates="eval_runs")
    prompt_version: Mapped[PromptVersion] = relationship(back_populates="eval_runs")
    model_config: Mapped[ModelConfig] = relationship(back_populates="eval_runs")
    results: Mapped[list[EvalResult]] = relationship(
        back_populates="eval_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    scorecard: Mapped[Scorecard | None] = relationship(
        back_populates="eval_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
