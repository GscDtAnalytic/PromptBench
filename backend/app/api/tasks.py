from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.evaluation.aggregate import WEIGHTS
from app.evaluation.judge import ANCHORS
from app.evaluation.task_checks import rubric_criteria, task_description
from app.models import PromptVersion, Task, TestCase
from app.schemas import (
    PromptVersionRead,
    RubricRead,
    TaskCreate,
    TaskRead,
    TestCaseRead,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRead])
async def list_tasks(db: AsyncSession = Depends(get_db)) -> list[Task]:
    result = await db.execute(select(Task).order_by(Task.id))
    return list(result.scalars().all())


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreate, db: AsyncSession = Depends(get_db)) -> Task:
    exists = await db.execute(select(Task).where(Task.slug == payload.slug))
    if exists.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail=f"task slug '{payload.slug}' já existe")
    task = Task(**payload.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)) -> Task:
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task não encontrada")
    return task


@router.get("/{task_id}/prompts", response_model=list[PromptVersionRead])
async def list_prompts(task_id: int, db: AsyncSession = Depends(get_db)) -> list[PromptVersion]:
    if (await db.get(Task, task_id)) is None:
        raise HTTPException(status_code=404, detail="task não encontrada")
    result = await db.execute(
        select(PromptVersion)
        .where(PromptVersion.task_id == task_id)
        .order_by(PromptVersion.version_number)
    )
    return list(result.scalars().all())


@router.get("/{task_id}/testcases", response_model=list[TestCaseRead])
async def list_testcases(task_id: int, db: AsyncSession = Depends(get_db)) -> list[TestCase]:
    if (await db.get(Task, task_id)) is None:
        raise HTTPException(status_code=404, detail="task não encontrada")
    result = await db.execute(
        select(TestCase).where(TestCase.task_id == task_id).order_by(TestCase.id)
    )
    return list(result.scalars().all())


@router.get("/{task_id}/rubric", response_model=RubricRead)
async def get_rubric(task_id: int, db: AsyncSession = Depends(get_db)) -> RubricRead:
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task não encontrada")
    return RubricRead(
        task_description=task_description(task.task_type),
        rubric_criteria=rubric_criteria(task.task_type),
        dimensions=[
            "quality",
            "instruction_adherence",
            "factual_structural",
            "tone_format",
        ],
        weights=WEIGHTS[task.task_type],
        anchors=ANCHORS.strip(),
    )
