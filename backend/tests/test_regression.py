"""
Testes do mecanismo de regressão (feature-âncora).

`compare_runs(baseline, candidate, thresholds)` recebe dois Scorecards e emite
`RegressionVerdictPayload`. O ponto central que provamos:
- score global pode subir enquanto um SLICE regride → veredito FALHA mesmo assim.
"""

from __future__ import annotations

from typing import Any

from app.evaluation.regression import compare_runs


class FakeSC:
    """Stand-in leve para Scorecard ORM — compare_runs só usa getattr."""

    def __init__(
        self,
        *,
        aggregate_score: float = 0.8,
        quality: float = 4.0,
        instruction_adherence: float = 4.0,
        factual_structural: float = 4.0,
        tone_format: float = 4.0,
        total_cost_usd: float = 0.001,
        avg_latency_ms: float = 120.0,
        failure_rate: float = 0.0,
        variance: float = 0.05,
        per_slice_breakdown: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.aggregate_score = aggregate_score
        self.quality = quality
        self.instruction_adherence = instruction_adherence
        self.factual_structural = factual_structural
        self.tone_format = tone_format
        self.total_cost_usd = total_cost_usd
        self.avg_latency_ms = avg_latency_ms
        self.failure_rate = failure_rate
        self.variance = variance
        self.per_slice_breakdown = per_slice_breakdown or {
            "typical": {"aggregate_score": 0.85},
            "edge": {"aggregate_score": 0.70},
            "known_failure": {"aggregate_score": 0.50},
            "adversarial": {"aggregate_score": 0.60},
        }


def test_identical_runs_pass() -> None:
    a = FakeSC()
    b = FakeSC()
    v = compare_runs(baseline=a, candidate=b)  # type: ignore[arg-type]
    assert v.passed
    assert v.failures == []


def test_candidate_strictly_better_passes() -> None:
    a = FakeSC()
    b = FakeSC(
        aggregate_score=0.9,
        quality=4.5,
        instruction_adherence=4.5,
        factual_structural=4.5,
        tone_format=4.5,
        per_slice_breakdown={
            "typical": {"aggregate_score": 0.90},
            "edge": {"aggregate_score": 0.80},
            "known_failure": {"aggregate_score": 0.60},
            "adversarial": {"aggregate_score": 0.70},
        },
    )
    v = compare_runs(baseline=a, candidate=b)  # type: ignore[arg-type]
    assert v.passed


def test_regression_in_slice_fails_even_if_global_improves() -> None:
    """
    O caso âncora: candidate melhora em typical mas REGRIDE em adversarial.
    Score global SOBE mas o veredito FALHA porque o slice quebra.
    """
    a = FakeSC(
        per_slice_breakdown={
            "typical": {"aggregate_score": 0.85},
            "edge": {"aggregate_score": 0.70},
            "known_failure": {"aggregate_score": 0.50},
            "adversarial": {"aggregate_score": 0.60},
        }
    )
    b = FakeSC(
        aggregate_score=0.85,  # global subiu
        per_slice_breakdown={
            "typical": {"aggregate_score": 0.95},  # melhorou
            "edge": {"aggregate_score": 0.75},
            "known_failure": {"aggregate_score": 0.55},
            "adversarial": {"aggregate_score": 0.20},  # CAIU 0.40
        },
    )
    v = compare_runs(baseline=a, candidate=b, max_slice_regression=0.10)  # type: ignore[arg-type]
    assert v.passed is False
    assert any("adversarial" in f for f in v.failures)
    adv_delta = next(s for s in v.slice_deltas if s.slice == "adversarial")
    assert adv_delta.passed is False
    assert adv_delta.delta < 0


def test_dimension_drop_fails() -> None:
    a = FakeSC(factual_structural=4.5)
    b = FakeSC(factual_structural=4.0)  # caiu 0.5
    # max_dimension_regression=0.05 → limite -0.25; cai 0.5 → falha
    v = compare_runs(baseline=a, candidate=b, max_dimension_regression=0.05)  # type: ignore[arg-type]
    assert v.passed is False
    assert any("factual_structural" in f for f in v.failures)


def test_cost_increase_above_threshold_fails() -> None:
    a = FakeSC(total_cost_usd=0.001)
    b = FakeSC(total_cost_usd=0.002)  # +100%
    v = compare_runs(baseline=a, candidate=b, max_cost_increase=0.20)  # type: ignore[arg-type]
    assert v.cost_passed is False
    assert any("custo" in f.lower() for f in v.failures)


def test_cost_neutral_or_lower_passes() -> None:
    a = FakeSC(total_cost_usd=0.001)
    b = FakeSC(total_cost_usd=0.001)
    v = compare_runs(baseline=a, candidate=b)  # type: ignore[arg-type]
    assert v.cost_passed is True


def test_per_slice_breakdown_exposes_count_unchanged() -> None:
    """Não invariável: compare não muda counts, apenas compara aggregate_score."""
    a = FakeSC(
        per_slice_breakdown={"typical": {"aggregate_score": 0.8, "count": 18.0}}
    )
    b = FakeSC(
        per_slice_breakdown={"typical": {"aggregate_score": 0.85, "count": 18.0}}
    )
    v = compare_runs(baseline=a, candidate=b)  # type: ignore[arg-type]
    typical = next(s for s in v.slice_deltas if s.slice == "typical")
    assert typical.passed is True
    assert typical.delta > 0


def test_new_slice_in_candidate_handled_gracefully() -> None:
    """
    Se o candidate tem um slice ausente no baseline, baseline aparece como 0.
    Como o candidate é > 0, a regressão é positiva (não falha).
    """
    a = FakeSC(
        per_slice_breakdown={"typical": {"aggregate_score": 0.8}}
    )
    b = FakeSC(
        per_slice_breakdown={
            "typical": {"aggregate_score": 0.85},
            "adversarial": {"aggregate_score": 0.7},
        }
    )
    v = compare_runs(baseline=a, candidate=b)  # type: ignore[arg-type]
    assert v.passed is True


def test_slice_removed_in_candidate_fails() -> None:
    """
    Slice presente no baseline mas ausente no candidate cai para 0 → regressão.
    """
    a = FakeSC(
        per_slice_breakdown={
            "typical": {"aggregate_score": 0.8},
            "adversarial": {"aggregate_score": 0.7},
        }
    )
    b = FakeSC(
        per_slice_breakdown={"typical": {"aggregate_score": 0.85}}
    )
    v = compare_runs(baseline=a, candidate=b)  # type: ignore[arg-type]
    assert v.passed is False
    assert any("adversarial" in f for f in v.failures)


def test_cost_delta_pct_for_zero_baseline() -> None:
    a = FakeSC(total_cost_usd=0.0)
    b = FakeSC(total_cost_usd=0.0)
    v = compare_runs(baseline=a, candidate=b)  # type: ignore[arg-type]
    assert v.cost_delta_pct == 0.0
    assert v.cost_passed is True
