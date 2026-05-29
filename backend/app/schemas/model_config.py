from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Provider


class ModelConfigCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    provider: Provider
    model_name: str = Field(min_length=1, max_length=120)
    temperature: float = 0.0
    max_tokens: int = 1024
    price_per_1m_input: float = Field(ge=0)
    price_per_1m_output: float = Field(ge=0)


class ModelConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    provider: Provider
    model_name: str
    temperature: float
    max_tokens: int
    price_per_1m_input: float
    price_per_1m_output: float
