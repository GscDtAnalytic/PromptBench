from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import SliceLabel

if TYPE_CHECKING:
    from app.models.eval_result import EvalResult
    from app.models.task import Task


class TestCase(Base):
    __tablename__ = "test_cases"
    __table_args__ = (Index("ix_testcase_task_slice", "task_id", "slice"),)
    __test__ = False  # silencia pytest "looks like a test class"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    input: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    expected: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    slice: Mapped[SliceLabel] = mapped_column(
        SAEnum(SliceLabel, name="slice_label"), nullable=False
    )
    rubric_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    task: Mapped[Task] = relationship(back_populates="test_cases")
    eval_results: Mapped[list[EvalResult]] = relationship(
        back_populates="test_case",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
