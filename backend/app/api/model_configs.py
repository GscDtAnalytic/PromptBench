from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models import ModelConfig
from app.schemas import ModelConfigCreate, ModelConfigRead

router = APIRouter(prefix="/model-configs", tags=["model-configs"])


@router.get("", response_model=list[ModelConfigRead])
async def list_model_configs(db: AsyncSession = Depends(get_db)) -> list[ModelConfig]:
    result = await db.execute(select(ModelConfig).order_by(ModelConfig.id))
    return list(result.scalars().all())


@router.post("", response_model=ModelConfigRead, status_code=status.HTTP_201_CREATED)
async def create_model_config(
    payload: ModelConfigCreate, db: AsyncSession = Depends(get_db)
) -> ModelConfig:
    mc = ModelConfig(**payload.model_dump())
    db.add(mc)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"conflito: {e}") from e
    await db.refresh(mc)
    return mc
