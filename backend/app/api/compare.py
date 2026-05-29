from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.evaluation.regression import compare_runs
from app.models import Scorecard
from app.schemas import ComparisonResult

router = APIRouter(tags=["compare"])


@router.get("/compare", response_model=ComparisonResult)
async def compare_endpoint(
    baseline: int = Query(..., description="run_id baseline"),
    candidate: int = Query(..., description="run_id candidate"),
    max_dimension_regression: float = 0.05,
    max_slice_regression: float = 0.10,
    max_cost_increase: float = 0.20,
    db: AsyncSession = Depends(get_db),
) -> ComparisonResult:
    sc_a = (
        await db.execute(select(Scorecard).where(Scorecard.eval_run_id == baseline))
    ).scalar_one_or_none()
    sc_b = (
        await db.execute(select(Scorecard).where(Scorecard.eval_run_id == candidate))
    ).scalar_one_or_none()
    if sc_a is None or sc_b is None:
        raise HTTPException(status_code=404, detail="scorecard ausente para baseline ou candidate")

    verdict = compare_runs(
        baseline=sc_a,
        candidate=sc_b,
        max_dimension_regression=max_dimension_regression,
        max_slice_regression=max_slice_regression,
        max_cost_increase=max_cost_increase,
    )
    return ComparisonResult(
        baseline_run_id=baseline,
        candidate_run_id=candidate,
        verdict=verdict,
    )
