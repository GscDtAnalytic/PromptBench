"""
Smoke test do FakeAdapter.

Executa um par de chamadas roteirizadas e imprime text/latency/tokens/cost,
provando que o pipeline de medição funciona ponta-a-ponta sem chave de API.

Uso:
  python -m scripts.smoke_adapter
"""

from __future__ import annotations

import asyncio
import json

from app.adapters import get_adapter
from app.core.pricing import compute_cost_usd
from app.models.enums import Provider

SCENARIOS = [
    ("task_a_resume_matching", "v1_baseline", "typical"),
    ("task_a_resume_matching", "v3_fewshot", "typical"),
    ("task_a_resume_matching", "v3_fewshot", "adversarial"),
    ("task_a_resume_matching", "v5_guardrails", "adversarial"),
    ("task_b_support", "v3_fewshot", "adversarial"),
]

# pricing exemplo (mesma escala dos providers reais)
PRICE_PER_1M_INPUT = 0.50
PRICE_PER_1M_OUTPUT = 1.50


async def main() -> None:
    adapter = get_adapter(Provider.fake, "fake-fast")

    print("smoke_adapter — provider=fake\n")
    for task_slug, version, slice_label in SCENARIOS:
        response = await adapter.call(
            system="You are a benchmark fixture.",
            user="Avalie.",
            params={
                "temperature": 0.0,
                "_scenario_hint": {
                    "task_slug": task_slug,
                    "prompt_version_name": version,
                    "slice": slice_label,
                    "input": {"placeholder": True},
                    "repetition_index": 0,
                },
            },
        )
        cost = compute_cost_usd(
            response.input_tokens,
            response.output_tokens,
            PRICE_PER_1M_INPUT,
            PRICE_PER_1M_OUTPUT,
        )

        try:
            parsed = json.loads(response.text)
            preview = json.dumps(parsed, ensure_ascii=False)[:120]
        except json.JSONDecodeError:
            preview = response.text[:120]

        print(
            f"[{task_slug:32}] {version:18} {slice_label:12} "
            f"in={response.input_tokens:4} out={response.output_tokens:4} "
            f"lat={response.latency_ms:4}ms cost=${cost:.6f}"
        )
        print(f"   → {preview}")


if __name__ == "__main__":
    asyncio.run(main())
