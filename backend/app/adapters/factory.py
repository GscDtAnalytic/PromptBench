from __future__ import annotations

from app.adapters.base import ModelAdapter
from app.adapters.fake import FakeAdapter
from app.core.config import get_settings
from app.models.enums import Provider


def get_adapter(provider: Provider, model_name: str) -> ModelAdapter:
    """
    Resolve adapter por provider.

    Adapters reais (Claude/OpenAI) só são importados sob demanda — assim o backend
    sobe mesmo sem as chaves configuradas e sem ter os SDKs imediatamente carregados.
    """
    settings = get_settings()

    if provider == Provider.fake:
        return FakeAdapter(model_name=model_name)

    if provider == Provider.claude:
        from app.adapters.claude import ClaudeAdapter

        return ClaudeAdapter(model_name=model_name, api_key=settings.anthropic_api_key)

    if provider == Provider.openai:
        from app.adapters.openai import OpenAIAdapter

        return OpenAIAdapter(model_name=model_name, api_key=settings.openai_api_key)

    if provider == Provider.gemini:
        from app.adapters.gemini import GeminiAdapter

        return GeminiAdapter(model_name=model_name)

    raise ValueError(f"Provider desconhecido: {provider}")
