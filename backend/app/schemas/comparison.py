from __future__ import annotations

from pydantic import BaseModel


class DimensionDelta(BaseModel):
    dimension: str
    baseline: float
    candidate: float
    delta: float
    passed: bool  # threshold respeitado


class SliceDelta(BaseModel):
    slice: str
    baseline_score: float
    candidate_score: float
    delta: float
    passed: bool


class RegressionVerdictPayload(BaseModel):
    """O veredito do mecanismo de regressão (bloco 7)."""

    passed: bool
    failures: list[str]
    dimension_deltas: list[DimensionDelta]
    slice_deltas: list[SliceDelta]
    cost_delta_pct: float
    cost_passed: bool


class ComparisonResult(BaseModel):
    baseline_run_id: int
    candidate_run_id: int
    verdict: RegressionVerdictPayload
