from __future__ import annotations

from enum import StrEnum


class TaskType(StrEnum):
    structured_extraction = "structured_extraction"
    classification_response = "classification_response"


class SliceLabel(StrEnum):
    typical = "typical"
    edge = "edge"
    known_failure = "known_failure"
    adversarial = "adversarial"


class Provider(StrEnum):
    fake = "fake"
    claude = "claude"
    openai = "openai"
    gemini = "gemini"


class RunStatus(StrEnum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"
