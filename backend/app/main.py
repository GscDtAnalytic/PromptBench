from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    compare,
    export,
    model_configs,
    prompts,
    runs,
    scorecards,
    tasks,
)
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    logger = get_logger("app")
    logger.info("backend.startup", provider=get_settings().model_provider)
    yield
    logger.info("backend.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="PromptBench Studio", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(tasks.router)
    app.include_router(prompts.router)
    app.include_router(model_configs.router)
    app.include_router(runs.router)
    app.include_router(scorecards.router)
    app.include_router(compare.router)
    app.include_router(export.router)
    return app


app = create_app()
