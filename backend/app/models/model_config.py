from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import Provider

if TYPE_CHECKING:
    from app.models.eval_run import EvalRun


class ModelConfig(Base):
    __tablename__ = "model_configs"
    __table_args__ = (UniqueConstraint("provider", "model_name", name="uq_model_provider_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[Provider] = mapped_column(
        SAEnum(Provider, name="provider"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    max_tokens: Mapped[int] = mapped_column(nullable=False, default=1024)
    price_per_1m_input: Mapped[float] = mapped_column(Float, nullable=False)
    price_per_1m_output: Mapped[float] = mapped_column(Float, nullable=False)

    eval_runs: Mapped[list[EvalRun]] = relationship(
        back_populates="model_config",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
