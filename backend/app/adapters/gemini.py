from __future__ import annotations

from typing import Any

from app.adapters.base import ModelAdapter, ModelResponse


class GeminiAdapter(ModelAdapter):
    """
    Stub que conforma à interface, pronto para plugar.

    Quando implementar de verdade, basta seguir o padrão de Claude/OpenAI:
    medir latência local, extrair tokens reais do usage, retry com backoff.
    """

    provider_name = "gemini"

    async def call(
        self, *, system: str, user: str, params: dict[str, Any]
    ) -> ModelResponse:
        raise NotImplementedError(
            "GeminiAdapter ainda não implementado. Interface está pronta para plugar."
        )
