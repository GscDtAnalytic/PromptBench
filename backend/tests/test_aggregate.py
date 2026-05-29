from __future__ import annotations

from app.evaluation.aggregate import EvalResultRecord, aggregate
from app.models.enums import SliceLabel, TaskType


def _rec(
    *,
    tc_id: int,
    slice_label: SliceLabel,
    rep: int,
    passed: bool = True,
    rubric: dict[str, int] | None = None,
    judge_error: bool = False,
    latency_ms: int = 100,
    cost_usd: float = 0.0001,
) -> EvalResultRecord:
    if judge_error:
        rubric_scores: dict[str, object] = {"judge_error": "x"}
    elif rubric is None:
        rubric_scores = {
            "quality": 4,
            "instruction_adherence": 4,
            "factual_structural": 4,
            "tone_format": 4,
        }
    else:
        rubric_scores = {**rubric}
    return EvalResultRecord(
        test_case_id=tc_id,
        slice=slice_label,
        repetition_index=rep,
        passed=passed,
        rubric_scores=rubric_scores,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
    )


def test_aggregate_empty_records() -> None:
    payload = aggregate([], TaskType.structured_extraction)
    assert payload.aggregate_score == 0.0
    assert payload.failure_rate == 0.0
    assert payload.per_slice_breakdown == {}


def test_aggregate_basic_all_passed() -> None:
    records = [
        _rec(tc_id=1, slice_label=SliceLabel.typical, rep=0),
        _rec(tc_id=1, slice_label=SliceLabel.typical, rep=1),
    ]
    payload = aggregate(records, TaskType.structured_extraction)
    # rubric tudo 4 → score normalizado (4-1)/4 = 0.75
    assert abs(payload.aggregate_score - 0.75) < 1e-9
    assert payload.failure_rate == 0.0
    # variance entre dois resultados idênticos = 0
    assert payload.variance == 0.0


def test_aggregate_failed_results_drag_score() -> None:
    records = [
        _rec(tc_id=1, slice_label=SliceLabel.typical, rep=0, passed=True),
        _rec(tc_id=2, slice_label=SliceLabel.typical, rep=0, passed=False),
    ]
    payload = aggregate(records, TaskType.structured_extraction)
    # 1 passou (0.75) + 1 falhou (0.0) → média 0.375
    assert abs(payload.aggregate_score - 0.375) < 1e-9
    assert payload.failure_rate == 0.5


def test_aggregate_slice_breakdown_exposes_per_slice_score() -> None:
    records = [
        _rec(tc_id=1, slice_label=SliceLabel.typical, rep=0, rubric={
            "quality": 5, "instruction_adherence": 5, "factual_structural": 5, "tone_format": 5
        }),
        _rec(tc_id=2, slice_label=SliceLabel.adversarial, rep=0, passed=False),
    ]
    payload = aggregate(records, TaskType.structured_extraction)
    assert "typical" in payload.per_slice_breakdown
    assert "adversarial" in payload.per_slice_breakdown
    assert payload.per_slice_breakdown["typical"]["aggregate_score"] == 1.0
    assert payload.per_slice_breakdown["adversarial"]["aggregate_score"] == 0.0
    assert payload.per_slice_breakdown["adversarial"]["failure_rate"] == 1.0


def test_aggregate_judge_error_treated_as_zero() -> None:
    records = [_rec(tc_id=1, slice_label=SliceLabel.typical, rep=0, judge_error=True)]
    payload = aggregate(records, TaskType.structured_extraction)
    assert payload.aggregate_score == 0.0


def test_aggregate_variance_between_repetitions() -> None:
    # mesmo test_case, 3 repetições com scores diferentes
    records = [
        _rec(tc_id=1, slice_label=SliceLabel.typical, rep=0, rubric={
            "quality": 5, "instruction_adherence": 5, "factual_structural": 5, "tone_format": 5
        }),
        _rec(tc_id=1, slice_label=SliceLabel.typical, rep=1, rubric={
            "quality": 3, "instruction_adherence": 3, "factual_structural": 3, "tone_format": 3
        }),
        _rec(tc_id=1, slice_label=SliceLabel.typical, rep=2, rubric={
            "quality": 1, "instruction_adherence": 1, "factual_structural": 1, "tone_format": 1
        }),
    ]
    payload = aggregate(records, TaskType.structured_extraction)
    assert payload.variance > 0.0


def test_aggregate_anti_halo_regression_visible_in_slice() -> None:
    """
    Caso âncora: prompt fortíssimo em typical (score 1.0 médio) e zerado em adversarial.
    A média global esconde — o breakdown por slice expõe.
    """
    records = (
        [_rec(tc_id=i, slice_label=SliceLabel.typical, rep=0, rubric={
            "quality": 5, "instruction_adherence": 5, "factual_structural": 5, "tone_format": 5
        }) for i in range(8)]
        + [_rec(tc_id=i + 100, slice_label=SliceLabel.adversarial, rep=0, passed=False) for i in range(2)]
    )
    payload = aggregate(records, TaskType.structured_extraction)
    # global = (8 × 1.0 + 2 × 0.0)/10 = 0.8 — parece bom
    assert abs(payload.aggregate_score - 0.8) < 1e-9
    # mas por slice o adversarial é 0
    assert payload.per_slice_breakdown["adversarial"]["aggregate_score"] == 0.0
    assert payload.per_slice_breakdown["typical"]["aggregate_score"] == 1.0


def test_aggregate_weights_differ_per_task_type() -> None:
    """
    structured_extraction pesa factual_structural=0.4
    classification_response pesa factual_structural=0.2
    """
    rubric = {
        "quality": 1,
        "instruction_adherence": 1,
        "factual_structural": 5,  # alto
        "tone_format": 1,
    }
    rec_se = _rec(tc_id=1, slice_label=SliceLabel.typical, rep=0, rubric=rubric)
    rec_cr = _rec(tc_id=1, slice_label=SliceLabel.typical, rep=0, rubric=rubric)

    se = aggregate([rec_se], TaskType.structured_extraction)
    cr = aggregate([rec_cr], TaskType.classification_response)
    # structured pesa mais factual=5 → score mais alto
    assert se.aggregate_score > cr.aggregate_score


def test_aggregate_per_slice_includes_count() -> None:
    records = [
        _rec(tc_id=1, slice_label=SliceLabel.typical, rep=0),
        _rec(tc_id=2, slice_label=SliceLabel.typical, rep=0),
        _rec(tc_id=3, slice_label=SliceLabel.edge, rep=0),
    ]
    payload = aggregate(records, TaskType.structured_extraction)
    assert payload.per_slice_breakdown["typical"]["count"] == 2.0
    assert payload.per_slice_breakdown["edge"]["count"] == 1.0


def test_aggregate_total_cost_and_avg_latency() -> None:
    records = [
        _rec(tc_id=1, slice_label=SliceLabel.typical, rep=0, latency_ms=100, cost_usd=0.001),
        _rec(tc_id=2, slice_label=SliceLabel.typical, rep=0, latency_ms=200, cost_usd=0.002),
    ]
    payload = aggregate(records, TaskType.structured_extraction)
    assert payload.avg_latency_ms == 150.0
    assert abs(payload.total_cost_usd - 0.003) < 1e-9
