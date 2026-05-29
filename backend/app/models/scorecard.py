from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.eval_run import EvalRun


class Scorecard(Base):
    __tablename__ = "scorecards"
    __table_args__ = (Index("ix_scorecard_run", "eval_run_id", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True)
    eval_run_id: Mapped[int] = mapped_column(
        ForeignKey("eval_runs.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    aggregate_score: Mapped[float] = mapped_column(Float, nullable=False)
    quality: Mapped[float] = mapped_column(Float, nullable=False)
    instruction_adherence: Mapped[float] = mapped_column(Float, nullable=False)
    factual_structural: Mapped[float] = mapped_column(Float, nullable=False)
    tone_format: Mapped[float] = mapped_column(Float, nullable=False)

    avg_latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    total_cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    failure_rate: Mapped[float] = mapped_column(Float, nullable=False)
    variance: Mapped[float] = mapped_column(Float, nullable=False)

    # {"typical": {"aggregate": .., "quality": .., "failure_rate": ..}, "edge": {...}, ...}
    per_slice_breakdown: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    eval_run: Mapped[EvalRun] = relationship(back_populates="scorecard")
