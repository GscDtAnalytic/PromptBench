from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PromptVersionCreate(BaseModel):
    # Pydantic v2 reserva model_* — desabilita o namespace para aceitar model_params.
    model_config = ConfigDict(protected_namespaces=())

    name: str = Field(min_length=1, max_length=200)
    system_prompt: str
    user_template: str
    model_params: dict[str, Any] = Field(default_factory=dict)
    is_baseline: bool = False


class PromptVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    task_id: int
    version_number: int
    name: str
    system_prompt: str
    user_template: str
    model_params: dict[str, Any]
    is_baseline: bool
    created_at: datetime


class PromptDiff(BaseModel):
    a_version: int
    b_version: int
    system_prompt_diff: str
    user_template_diff: str
