from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import RunStatus


class RecentRunEntry(BaseModel):
    eval_run_id: int
    task_id: int
    task_slug: str
    task_name: str
    prompt_version_name: str
    version_number: int
    model_name: str
    status: RunStatus
    aggregate_score: float | None
    created_at: datetime
