from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+asyncpg://promptbench:promptbench@localhost:5432/promptbench"
    )
    database_url_sync: str = Field(
        default="postgresql+psycopg://promptbench:promptbench@localhost:5432/promptbench"
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    model_provider: Literal["fake", "claude", "openai", "gemini"] = Field(default="fake")
    anthropic_api_key: str | None = Field(default=None)
    openai_api_key: str | None = Field(default=None)
    gemini_api_key: str | None = Field(default=None)

    # Judge fixo (anti-viés): se definidos, o LLM-as-judge usa SEMPRE este
    # provider/model, independentemente do modelo candidato avaliado. Se ficarem
    # None, o judge cai no comportamento legado (usa o mesmo modelo do run).
    # Em produção: aponte para um modelo forte e estável (ex.: claude-sonnet-4-6).
    judge_provider: Literal["fake", "claude", "openai", "gemini"] | None = Field(default=None)
    judge_model: str | None = Field(default=None)

    log_level: str = Field(default="INFO")
    cors_origins: str = Field(default="http://localhost:3000")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
