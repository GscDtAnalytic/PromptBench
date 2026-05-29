from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RunStatus, SliceLabel


class EvalRunCreate(BaseModel):
    task_id: int
    prompt_version_id: int
    model_config_id: int
    repetitions: int = Field(default=3, ge=1, le=10)


class EvalRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    prompt_version_id: int
    model_config_id: int
    status: RunStatus
    repetitions: int
    created_at: datetime
    finished_at: datetime | None


class EvalRunStatusRead(BaseModel):
    """Status + progresso para polling do frontend."""

    id: int
    status: RunStatus
    total_expected: int
    completed: int
    progress: float  # 0.0 a 1.0


class EvalResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    eval_run_id: int
    test_case_id: int
    repetition_index: int
    raw_output: str | None
    latency_ms: int | None
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None
    deterministic_scores: dict[str, Any] | None
    rubric_scores: dict[str, Any] | None
    passed: bool
    error: str | None
    slice: SliceLabel | None = None  # injetado a partir do test_case
