from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.enums import SliceLabel


class TestCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    input: dict[str, Any]
    expected: dict[str, Any] | None
    slice: SliceLabel
    rubric_notes: str | None
