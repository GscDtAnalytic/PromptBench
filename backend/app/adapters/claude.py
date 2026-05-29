from __future__ import annotations

import time
from typing import Any

from anthropic import AsyncAnthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.adapters.base import ModelAdapter, ModelResponse


class ClaudeAdapter(ModelAdapter):
    provider_name = "claude"

    def __init__(self, model_name: str, api_key: str | None = None) -> None:
        super().__init__(model_name)
        self._client = AsyncAnthropic(api_key=api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _call_with_retry(self, **kwargs: Any) -> Any:
        return await self._client.messages.create(**kwargs)

    async def call(
        self, *, system: str, user: str, params: dict[str, Any]
    ) -> ModelResponse:
        clean = self._public_params(params)
        temperature = float(clean.get("temperature", 0.0))
        max_tokens = int(clean.get("max_tokens", 1024))

        start = time.perf_counter()
        response = await self._call_with_retry(
            model=self.model_name,
            system=system,
            messages=[{"role": "user", "content": user}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        # response.content é uma lista de blocos; usa-se o primeiro `text` block.
        text_parts = [
            block.text for block in response.content if getattr(block, "type", "") == "text"
        ]
        text = "".join(text_parts)

        usage = response.usage
        return ModelResponse(
            text=text,
            input_tokens=int(usage.input_tokens),
            output_tokens=int(usage.output_tokens),
            latency_ms=elapsed_ms,
            raw={
                "provider": "claude",
                "model": self.model_name,
                "stop_reason": getattr(response, "stop_reason", None),
            },
        )
