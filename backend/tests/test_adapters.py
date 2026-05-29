from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.adapters import get_adapter
from app.adapters.base import ModelResponse
from app.adapters.fake import FakeAdapter
from app.core.pricing import compute_cost_usd
from app.models.enums import Provider

# =====================================================================
# FakeAdapter
# =====================================================================


@pytest.fixture
def fake() -> FakeAdapter:
    return FakeAdapter(model_name="fake-fast")


async def test_fake_returns_modelresponse(fake: FakeAdapter) -> None:
    response = await fake.call(
        system="You are a helpful assistant.",
        user="hi",
        params={"_scenario_hint": {
            "task_slug": "task_a_resume_matching",
            "prompt_version_name": "v3_fewshot",
            "slice": "typical",
            "input": {},
            "repetition_index": 0,
        }},
    )
    assert isinstance(response, ModelResponse)
    assert response.text
    assert response.input_tokens > 0
    assert response.output_tokens > 0
    assert response.latency_ms >= 0
    assert response.raw["provider"] == "fake"


async def test_fake_is_deterministic_for_same_hint(fake: FakeAdapter) -> None:
    hint = {
        "task_slug": "task_a_resume_matching",
        "prompt_version_name": "v3_fewshot",
        "slice": "typical",
        "input": {},
        "repetition_index": 1,
    }
    r1 = await fake.call(system="s", user="u", params={"_scenario_hint": hint})
    r2 = await fake.call(system="s", user="u", params={"_scenario_hint": hint})
    assert r1.text == r2.text


async def test_fake_varies_across_repetitions(fake: FakeAdapter) -> None:
    # variância simulada: reps diferentes devem produzir outputs diferentes em v1
    hints = [
        {
            "task_slug": "task_a_resume_matching",
            "prompt_version_name": "v1_baseline",
            "slice": "typical",
            "input": {},
            "repetition_index": i,
        }
        for i in range(3)
    ]
    outputs = [
        (await fake.call(system="s", user="u", params={"_scenario_hint": h})).text
        for h in hints
    ]
    assert len(set(outputs)) > 1, "v1 deveria ter variância entre repetições"


async def test_fake_regression_case_v3_adversarial(fake: FakeAdapter) -> None:
    """
    O caso âncora: v3-fewshot é forte em typical mas regride em adversarial.
    Em adversarial, o output cai no prompt injection (match_score=100, sem missing).
    """
    typical = await fake.call(
        system="s",
        user="u",
        params={"_scenario_hint": {
            "task_slug": "task_a_resume_matching",
            "prompt_version_name": "v3_fewshot",
            "slice": "typical",
            "input": {},
            "repetition_index": 0,
        }},
    )
    adversarial = await fake.call(
        system="s",
        user="u",
        params={"_scenario_hint": {
            "task_slug": "task_a_resume_matching",
            "prompt_version_name": "v3_fewshot",
            "slice": "adversarial",
            "input": {},
            "repetition_index": 0,
        }},
    )
    adv = json.loads(adversarial.text)
    assert adv["match_score"] == 100, "adversarial deveria mostrar inflação por injection"
    assert adv["missing_skills"] == []
    typ = json.loads(typical.text)
    assert typ["match_score"] < 100
    assert typ["missing_skills"]


async def test_fake_v5_resists_injection(fake: FakeAdapter) -> None:
    """v5-guardrails deveria não inflacionar em adversarial."""
    adv = await fake.call(
        system="s",
        user="u",
        params={"_scenario_hint": {
            "task_slug": "task_a_resume_matching",
            "prompt_version_name": "v5_guardrails",
            "slice": "adversarial",
            "input": {},
            "repetition_index": 0,
        }},
    )
    data = json.loads(adv.text)
    assert data["match_score"] < 90
    assert "ignored" in data["ranking_justification"].lower() or "ignorad" in data[
        "ranking_justification"
    ].lower()


async def test_fake_underscore_params_not_leaked(fake: FakeAdapter) -> None:
    # Garante que utility filtra chaves _-prefixed (importante p/ adapters reais).
    cleaned = FakeAdapter._public_params({"temperature": 0.0, "_scenario_hint": {}})
    assert "_scenario_hint" not in cleaned
    assert "temperature" in cleaned


# =====================================================================
# Factory
# =====================================================================


def test_factory_returns_fake() -> None:
    adapter = get_adapter(Provider.fake, "fake-model")
    assert isinstance(adapter, FakeAdapter)
    assert adapter.model_name == "fake-model"


def test_factory_gemini_raises_on_call() -> None:
    import asyncio

    adapter = get_adapter(Provider.gemini, "gemini-pro")
    with pytest.raises(NotImplementedError):
        asyncio.run(adapter.call(system="s", user="u", params={}))


# =====================================================================
# Pricing
# =====================================================================


def test_compute_cost_usd_basic() -> None:
    # 1M tokens × $1 = $1.0; 100k × $1 = $0.10
    cost = compute_cost_usd(
        input_tokens=100_000,
        output_tokens=0,
        price_per_1m_input=1.0,
        price_per_1m_output=2.0,
    )
    assert cost == 0.1


def test_compute_cost_usd_split() -> None:
    # 1000 in × $3/1M + 500 out × $15/1M = 0.003 + 0.0075 = 0.0105
    cost = compute_cost_usd(
        input_tokens=1000,
        output_tokens=500,
        price_per_1m_input=3.0,
        price_per_1m_output=15.0,
    )
    assert abs(cost - 0.0105) < 1e-9


# =====================================================================
# Claude e OpenAI adapters (mocked — não chama HTTP real)
# =====================================================================


async def test_claude_adapter_normalizes_response() -> None:
    from app.adapters.claude import ClaudeAdapter

    adapter = ClaudeAdapter(model_name="claude-test", api_key="sk-test")

    fake_block = MagicMock()
    fake_block.type = "text"
    fake_block.text = '{"match_score": 80}'

    fake_response = MagicMock()
    fake_response.content = [fake_block]
    fake_response.usage.input_tokens = 123
    fake_response.usage.output_tokens = 45
    fake_response.stop_reason = "end_turn"

    adapter._client.messages.create = AsyncMock(return_value=fake_response)  # type: ignore[method-assign]

    response = await adapter.call(system="s", user="u", params={"temperature": 0.0})
    assert response.text == '{"match_score": 80}'
    assert response.input_tokens == 123
    assert response.output_tokens == 45
    assert response.latency_ms >= 0
    assert response.raw["provider"] == "claude"


async def test_openai_adapter_normalizes_response() -> None:
    from app.adapters.openai import OpenAIAdapter

    adapter = OpenAIAdapter(model_name="gpt-test", api_key="sk-test")

    fake_choice = MagicMock()
    fake_choice.message.content = '{"category": "billing"}'
    fake_choice.finish_reason = "stop"

    fake_usage = MagicMock()
    fake_usage.prompt_tokens = 200
    fake_usage.completion_tokens = 80

    fake_response = MagicMock()
    fake_response.choices = [fake_choice]
    fake_response.usage = fake_usage

    adapter._client.chat.completions.create = AsyncMock(return_value=fake_response)  # type: ignore[method-assign]

    response = await adapter.call(system="s", user="u", params={"temperature": 0.0})
    assert response.text == '{"category": "billing"}'
    assert response.input_tokens == 200
    assert response.output_tokens == 80
    assert response.raw["provider"] == "openai"


async def test_adapter_ignores_internal_params() -> None:
    """Adapters reais não devem repassar `_scenario_hint` ao provedor (chave interna)."""
    from app.adapters.claude import ClaudeAdapter

    adapter = ClaudeAdapter(model_name="claude-test", api_key="sk-test")

    captured: dict[str, Any] = {}

    async def capture(**kwargs: Any) -> MagicMock:
        captured.update(kwargs)
        fake_block = MagicMock()
        fake_block.type = "text"
        fake_block.text = "ok"
        fake_response = MagicMock()
        fake_response.content = [fake_block]
        fake_response.usage.input_tokens = 1
        fake_response.usage.output_tokens = 1
        fake_response.stop_reason = "end_turn"
        return fake_response

    adapter._client.messages.create = capture  # type: ignore[method-assign]

    await adapter.call(
        system="s",
        user="u",
        params={"temperature": 0.5, "_scenario_hint": {"leak": True}},
    )
    # garante que params internos NÃO vazaram via kwargs do client
    for v in captured.values():
        if isinstance(v, dict):
            assert "_scenario_hint" not in v
