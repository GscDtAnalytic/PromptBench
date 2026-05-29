from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.eval_run import EvalRun
    from app.models.test_case import TestCase


class EvalResult(Base):
    __tablename__ = "eval_results"
    __table_args__ = (
        Index("ix_evalresult_run", "eval_run_id"),
        Index("ix_evalresult_run_case_rep", "eval_run_id", "test_case_id", "repetition_index"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    eval_run_id: Mapped[int] = mapped_column(
        ForeignKey("eval_runs.id", ondelete="CASCADE"), nullable=False
    )
    test_case_id: Mapped[int] = mapped_column(
        ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False
    )
    repetition_index: Mapped[int] = mapped_column(Integer, nullable=False)

    raw_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    # checks determinísticos: {check_name: {passed, score, detail}}
    deterministic_scores: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # rubric: {quality, instruction_adherence, factual_structural, tone_format, reasoning}
    # ou {"judge_error": "..."} se o judge falhar.
    rubric_scores: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    eval_run: Mapped[EvalRun] = relationship(back_populates="results")
    test_case: Mapped[TestCase] = relationship(back_populates="eval_results")
