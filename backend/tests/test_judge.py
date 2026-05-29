from __future__ import annotations

from typing import Any

from app.adapters.base import ModelAdapter, ModelResponse
from app.evaluation.judge import (
    RubricError,
    RubricInputs,
    RubricJudge,
    RubricOutputs,
)


class ScriptedAdapter(ModelAdapter):
    """Adapter de teste que devolve respostas pré-definidas em ordem."""

    provider_name = "scripted"

    def __init__(self, responses: list[str]) -> None:
        super().__init__(model_name="scripted")
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    async def call(
        self, *, system: str, user: str, params: dict[str, Any]
    ) -> ModelResponse:
        text = self.responses.pop(0) if self.responses else ""
        self.calls.append({"system": system, "user": user, "params": params})
        return ModelResponse(
            text=text,
            input_tokens=10,
            output_tokens=20,
            latency_ms=42,
            raw={},
        )


def _inputs() -> RubricInputs:
    return RubricInputs(
        task_description="Avalie o output.",
        test_case_input={"x": 1},
        candidate_output='{"match_score": 80}',
        rubric_criteria="quality, adherence, factual, tone (1-5 cada)",
    )


async def test_judge_returns_outputs_on_valid_json() -> None:
    adapter = ScriptedAdapter(
        responses=[
            '{"reasoning": "ok", "quality": 4, "instruction_adherence": 5, '
            '"factual_structural": 4, "tone_format": 4}'
        ]
    )
    judge = RubricJudge(adapter=adapter)
    result = await judge.judge(_inputs())
    assert isinstance(result, RubricOutputs)
    assert result.quality == 4
    assert result.instruction_adherence == 5
    assert not result.is_error


async def test_judge_extracts_json_from_noisy_response() -> None:
    """Judge deve achar o JSON mesmo se o LLM colocar prosa antes/depois."""
    adapter = ScriptedAdapter(
        responses=[
            "Aqui está minha avaliação:\n"
            '{"reasoning": "boa", "quality": 5, "instruction_adherence": 5, '
            '"factual_structural": 5, "tone_format": 5}\n'
            "Espero ter ajudado."
        ]
    )
    judge = RubricJudge(adapter=adapter)
    result = await judge.judge(_inputs())
    assert isinstance(result, RubricOutputs)
    assert result.quality == 5


async def test_judge_retries_once_then_error() -> None:
    adapter = ScriptedAdapter(
        responses=["lixo sem JSON", "ainda lixo sem JSON nenhum"]
    )
    judge = RubricJudge(adapter=adapter, retries=1)
    result = await judge.judge(_inputs())
    assert isinstance(result, RubricError)
    assert result.judge_error
    assert "JSON" in result.judge_error or "inválido" in result.judge_error.lower()
    # 1 tentativa + 1 retry = 2 chamadas
    assert len(adapter.calls) == 2


async def test_judge_succeeds_after_retry() -> None:
    adapter = ScriptedAdapter(
        responses=[
            "primeira tentativa quebrada",
            '{"reasoning": "...", "quality": 3, "instruction_adherence": 3, '
            '"factual_structural": 3, "tone_format": 3}',
        ]
    )
    judge = RubricJudge(adapter=adapter, retries=1)
    result = await judge.judge(_inputs())
    assert isinstance(result, RubricOutputs)
    assert result.quality == 3
    # segunda chamada deve ter a instrução de correção
    second_user = adapter.calls[1]["user"]
    assert "anterior" in second_user.lower() or "novamente" in second_user.lower()


async def test_judge_rejects_scores_out_of_range() -> None:
    adapter = ScriptedAdapter(
        responses=[
            '{"reasoning": "x", "quality": 6, "instruction_adherence": 3, '
            '"factual_structural": 3, "tone_format": 3}',
            '{"reasoning": "x", "quality": 6, "instruction_adherence": 3, '
            '"factual_structural": 3, "tone_format": 3}',
        ]
    )
    judge = RubricJudge(adapter=adapter, retries=1)
    result = await judge.judge(_inputs())
    assert isinstance(result, RubricError)


async def test_judge_temperature_is_zero_by_default() -> None:
    adapter = ScriptedAdapter(
        responses=[
            '{"reasoning": "x", "quality": 4, "instruction_adherence": 4, '
            '"factual_structural": 4, "tone_format": 4}'
        ]
    )
    judge = RubricJudge(adapter=adapter)
    await judge.judge(_inputs())
    assert adapter.calls[0]["params"]["temperature"] == 0.0


async def test_judge_anti_halo_in_prompt() -> None:
    """O prompt do judge deve instruir avaliação independente das dimensões."""
    adapter = ScriptedAdapter(
        responses=[
            '{"reasoning": "x", "quality": 4, "instruction_adherence": 4, '
            '"factual_structural": 4, "tone_format": 4}'
        ]
    )
    judge = RubricJudge(adapter=adapter)
    await judge.judge(_inputs())
    system = adapter.calls[0]["system"]
    assert "halo" in system.lower() or "independente" in system.lower()


async def test_judge_many_shot_anchors_in_prompt() -> None:
    adapter = ScriptedAdapter(
        responses=[
            '{"reasoning": "x", "quality": 4, "instruction_adherence": 4, '
            '"factual_structural": 4, "tone_format": 4}'
        ]
    )
    judge = RubricJudge(adapter=adapter)
    await judge.judge(_inputs())
    user = adapter.calls[0]["user"]
    assert "ÂNCORAS" in user or "Anchor" in user
