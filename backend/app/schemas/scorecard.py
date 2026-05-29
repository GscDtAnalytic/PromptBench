from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ScorecardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    eval_run_id: int
    aggregate_score: float
    quality: float
    instruction_adherence: float
    factual_structural: float
    tone_format: float
    avg_latency_ms: float
    total_cost_usd: float
    failure_rate: float
    variance: float
    per_slice_breakdown: dict[str, Any]


class LeaderboardEntry(BaseModel):
    eval_run_id: int
    prompt_version_id: int
    prompt_version_name: str
    version_number: int
    model_config_id: int
    model_name: str
    aggregate_score: float
    avg_latency_ms: float
    total_cost_usd: float
    failure_rate: float
