from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.eval_run import EvalRun
    from app.models.task import Task


class PromptVersion(Base):
    """
    IMUTÁVEL. Nunca atualize uma linha existente. Crie sempre uma nova versão
    com version_number = max(existing) + 1 em transação atômica.
    """

    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint("task_id", "version_number", name="uq_prompt_task_version"),
        Index("ix_prompt_task_version", "task_id", "version_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_template: Mapped[str] = mapped_column(Text, nullable=False)
    model_params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    is_baseline: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    task: Mapped[Task] = relationship(back_populates="prompt_versions")
    eval_runs: Mapped[list[EvalRun]] = relationship(
        back_populates="prompt_version",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
