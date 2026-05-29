from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import EvalRun, ModelConfig, PromptVersion, Scorecard, Task
from app.schemas import LeaderboardEntry, ScorecardRead

router = APIRouter(tags=["scorecards"])


@router.get("/scorecards/{run_id}", response_model=ScorecardRead)
async def get_scorecard(run_id: int, db: AsyncSession = Depends(get_db)) -> Scorecard:
    result = await db.execute(select(Scorecard).where(Scorecard.eval_run_id == run_id))
    sc = result.scalar_one_or_none()
    if sc is None:
        raise HTTPException(status_code=404, detail="scorecard ainda não disponível")
    return sc


@router.get("/tasks/{task_id}/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard(
    task_id: int, db: AsyncSession = Depends(get_db)
) -> list[LeaderboardEntry]:
    if (await db.get(Task, task_id)) is None:
        raise HTTPException(status_code=404, detail="task não encontrada")

    stmt = (
        select(
            Scorecard,
            EvalRun.id.label("run_id"),
            PromptVersion.id.label("pv_id"),
            PromptVersion.name.label("pv_name"),
            PromptVersion.version_number,
            ModelConfig.id.label("mc_id"),
            ModelConfig.model_name,
        )
        .join(EvalRun, Scorecard.eval_run_id == EvalRun.id)
        .join(PromptVersion, EvalRun.prompt_version_id == PromptVersion.id)
        .join(ModelConfig, EvalRun.model_config_id == ModelConfig.id)
        .where(EvalRun.task_id == task_id)
        .order_by(Scorecard.aggregate_score.desc())
    )
    rows = await db.execute(stmt)
    out: list[LeaderboardEntry] = []
    for sc, run_id, pv_id, pv_name, vnum, mc_id, mname in rows.all():
        out.append(
            LeaderboardEntry(
                eval_run_id=run_id,
                prompt_version_id=pv_id,
                prompt_version_name=pv_name,
                version_number=vnum,
                model_config_id=mc_id,
                model_name=mname,
                aggregate_score=sc.aggregate_score,
                avg_latency_ms=sc.avg_latency_ms,
                total_cost_usd=sc.total_cost_usd,
                failure_rate=sc.failure_rate,
            )
        )
    return out
