from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModelResponse:
    """
    Resposta normalizada de qualquer adapter.

    Custo NÃO está aqui — fica numa camada acima (ver core.pricing.compute_cost_usd),
    porque pricing pertence à ModelConfig, não ao adapter.
    """

    text: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    raw: dict[str, Any] = field(default_factory=dict)


class ModelAdapter(ABC):
    """Contrato uniforme entre Fake/Claude/OpenAI/Gemini."""

    provider_name: str

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    @abstractmethod
    async def call(
        self, *, system: str, user: str, params: dict[str, Any]
    ) -> ModelResponse:
        """
        Executa uma chamada ao modelo. `params` pode conter:
        - `temperature`, `max_tokens`: passados ao provedor
        - `_scenario_hint`: somente lido pelo FakeAdapter (worker injeta), ignorado
          pelos adapters reais

        DEVE medir latência localmente (não confiar no provedor) e extrair `usage`
        real (não estimar tokens).
        """

    @staticmethod
    def _public_params(params: dict[str, Any]) -> dict[str, Any]:
        """Remove chaves internas (prefixadas com _) antes de passar ao provedor."""
        return {k: v for k, v in params.items() if not k.startswith("_")}
