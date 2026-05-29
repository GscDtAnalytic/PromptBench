from __future__ import annotations

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.db import get_db
from app.models import (
    EvalResult,
    EvalRun,
    ModelConfig,
    PromptVersion,
    Scorecard,
    Task,
    TestCase,
)
from app.models.enums import RunStatus
from app.schemas import (
    EvalResultRead,
    EvalRunCreate,
    EvalRunRead,
    EvalRunStatusRead,
    RecentRunEntry,
)

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/recent", response_model=list[RecentRunEntry])
async def list_recent_runs(
    limit: int = 8, db: AsyncSession = Depends(get_db)
) -> list[RecentRunEntry]:
    """Últimos N runs com info combinada (task + prompt + modelo + score)."""
    stmt = (
        select(
            EvalRun.id,
            EvalRun.task_id,
            Task.slug,
            Task.name,
            PromptVersion.name,
            PromptVersion.version_number,
            ModelConfig.model_name,
            EvalRun.status,
            Scorecard.aggregate_score,
            EvalRun.created_at,
        )
        .join(Task, EvalRun.task_id == Task.id)
        .join(PromptVersion, EvalRun.prompt_version_id == PromptVersion.id)
        .join(ModelConfig, EvalRun.model_config_id == ModelConfig.id)
        .outerjoin(Scorecard, Scorecard.eval_run_id == EvalRun.id)
        .order_by(EvalRun.created_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    return [
        RecentRunEntry(
            eval_run_id=row[0],
            task_id=row[1],
            task_slug=row[2],
            task_name=row[3],
            prompt_version_name=row[4],
            version_number=row[5],
            model_name=row[6],
            status=row[7],
            aggregate_score=row[8],
            created_at=row[9],
        )
        for row in rows
    ]


@router.post("", response_model=EvalRunRead, status_code=status.HTTP_201_CREATED)
async def create_run(
    payload: EvalRunCreate, db: AsyncSession = Depends(get_db)
) -> EvalRun:
    task = await db.get(Task, payload.task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task não encontrada")
    if (await db.get(PromptVersion, payload.prompt_version_id)) is None:
        raise HTTPException(status_code=404, detail="prompt_version não encontrada")
    if (await db.get(ModelConfig, payload.model_config_id)) is None:
        raise HTTPException(status_code=404, detail="model_config não encontrado")

    run = EvalRun(
        task_id=payload.task_id,
        prompt_version_id=payload.prompt_version_id,
        model_config_id=payload.model_config_id,
        status=RunStatus.pending,
        repetitions=payload.repetitions,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # enfileira no arq
    settings = get_settings()
    redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        await redis.enqueue_job("run_eval_run", run.id)
    finally:
        await redis.close()
    return run


@router.get("/{run_id}", response_model=EvalRunRead)
async def get_run(run_id: int, db: AsyncSession = Depends(get_db)) -> EvalRun:
    run = await db.get(EvalRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run não encontrado")
    return run


@router.get("/{run_id}/status", response_model=EvalRunStatusRead)
async def get_run_status(run_id: int, db: AsyncSession = Depends(get_db)) -> EvalRunStatusRead:
    run = await db.get(EvalRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run não encontrado")
    n_cases = await db.scalar(
        select(func.count()).select_from(TestCase).where(TestCase.task_id == run.task_id)
    )
    total_expected = int(n_cases or 0) * run.repetitions
    completed = await db.scalar(
        select(func.count()).select_from(EvalResult).where(EvalResult.eval_run_id == run.id)
    )
    completed_n = int(completed or 0)
    progress = (completed_n / total_expected) if total_expected else 0.0
    return EvalRunStatusRead(
        id=run.id,
        status=run.status,
        total_expected=total_expected,
        completed=completed_n,
        progress=progress,
    )


@router.get("/{run_id}/results", response_model=list[EvalResultRead])
async def list_results(run_id: int, db: AsyncSession = Depends(get_db)) -> list[EvalResultRead]:
    if (await db.get(EvalRun, run_id)) is None:
        raise HTTPException(status_code=404, detail="run não encontrado")
    stmt = (
        select(EvalResult)
        .options(selectinload(EvalResult.test_case))
        .where(EvalResult.eval_run_id == run_id)
        .order_by(EvalResult.test_case_id, EvalResult.repetition_index)
    )
    result = await db.execute(stmt)
    rows: list[EvalResultRead] = []
    for er in result.scalars().all():
        read = EvalResultRead.model_validate(er, from_attributes=True)
        read.slice = er.test_case.slice
        rows.append(read)
    return rows
