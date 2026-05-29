from __future__ import annotations

import difflib

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import PromptVersion, Task
from app.schemas import PromptDiff, PromptVersionCreate, PromptVersionRead

router = APIRouter(prefix="/tasks/{task_id}/prompts", tags=["prompts"])


@router.post(
    "", response_model=PromptVersionRead, status_code=status.HTTP_201_CREATED
)
async def create_prompt_version(
    task_id: int,
    payload: PromptVersionCreate,
    db: AsyncSession = Depends(get_db),
) -> PromptVersion:
    """
    Cria uma NOVA versão. PromptVersion é imutável — não há UPDATE/PATCH.
    """
    if (await db.get(Task, task_id)) is None:
        raise HTTPException(status_code=404, detail="task não encontrada")

    max_version = await db.scalar(
        select(func.coalesce(func.max(PromptVersion.version_number), 0)).where(
            PromptVersion.task_id == task_id
        )
    )
    new_version = (max_version or 0) + 1

    pv = PromptVersion(
        task_id=task_id,
        version_number=new_version,
        name=payload.name,
        system_prompt=payload.system_prompt,
        user_template=payload.user_template,
        model_params=payload.model_params,
        is_baseline=payload.is_baseline,
    )
    db.add(pv)
    await db.commit()
    await db.refresh(pv)
    return pv


@router.get("/{version_number}", response_model=PromptVersionRead)
async def get_prompt_version(
    task_id: int, version_number: int, db: AsyncSession = Depends(get_db)
) -> PromptVersion:
    result = await db.execute(
        select(PromptVersion).where(
            PromptVersion.task_id == task_id,
            PromptVersion.version_number == version_number,
        )
    )
    pv = result.scalar_one_or_none()
    if pv is None:
        raise HTTPException(status_code=404, detail="versão não encontrada")
    return pv


@router.get("/diff", response_model=PromptDiff)
async def diff_prompts(
    task_id: int,
    a: int = Query(..., description="version_number da primeira"),
    b: int = Query(..., description="version_number da segunda"),
    db: AsyncSession = Depends(get_db),
) -> PromptDiff:
    async def fetch(v: int) -> PromptVersion:
        result = await db.execute(
            select(PromptVersion).where(
                PromptVersion.task_id == task_id,
                PromptVersion.version_number == v,
            )
        )
        pv = result.scalar_one_or_none()
        if pv is None:
            raise HTTPException(status_code=404, detail=f"versão {v} não encontrada")
        return pv

    pa = await fetch(a)
    pb = await fetch(b)
    return PromptDiff(
        a_version=a,
        b_version=b,
        system_prompt_diff="\n".join(
            difflib.unified_diff(
                pa.system_prompt.splitlines(),
                pb.system_prompt.splitlines(),
                fromfile=f"v{a}",
                tofile=f"v{b}",
                lineterm="",
            )
        ),
        user_template_diff="\n".join(
            difflib.unified_diff(
                pa.user_template.splitlines(),
                pb.user_template.splitlines(),
                fromfile=f"v{a}",
                tofile=f"v{b}",
                lineterm="",
            )
        ),
    )
