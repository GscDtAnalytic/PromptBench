from __future__ import annotations

import time
from typing import Any

from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.adapters.base import ModelAdapter, ModelResponse


class OpenAIAdapter(ModelAdapter):
    provider_name = "openai"

    def __init__(self, model_name: str, api_key: str | None = None) -> None:
        super().__init__(model_name)
        self._client = AsyncOpenAI(api_key=api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _call_with_retry(self, **kwargs: Any) -> Any:
        return await self._client.chat.completions.create(**kwargs)

    async def call(
        self, *, system: str, user: str, params: dict[str, Any]
    ) -> ModelResponse:
        clean = self._public_params(params)
        temperature = float(clean.get("temperature", 0.0))
        max_tokens = int(clean.get("max_tokens", 1024))

        start = time.perf_counter()
        response = await self._call_with_retry(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        choice = response.choices[0]
        text = choice.message.content or ""

        usage = response.usage
        input_tokens = int(getattr(usage, "prompt_tokens", 0)) if usage else 0
        output_tokens = int(getattr(usage, "completion_tokens", 0)) if usage else 0

        return ModelResponse(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=elapsed_ms,
            raw={
                "provider": "openai",
                "model": self.model_name,
                "finish_reason": choice.finish_reason,
            },
        )
