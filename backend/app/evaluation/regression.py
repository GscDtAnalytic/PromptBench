"""
Mecanismo de regressão — feature-âncora.

Função pura `compare_runs(baseline, candidate, thresholds) -> RegressionVerdictPayload`.

Implementação completa fica no Bloco 7; aqui já temos o esqueleto para o endpoint
/compare resolver imports limpos.
"""

from __future__ import annotations

from app.models import Scorecard
from app.schemas.comparison import (
    DimensionDelta,
    RegressionVerdictPayload,
    SliceDelta,
)

DIMENSIONS = ["quality", "instruction_adherence", "factual_structural", "tone_format"]


def _pct_change(old: float, new: float) -> float:
    if old == 0:
        return 0.0 if new == 0 else float("inf")
    return (new - old) / abs(old)


def compare_runs(
    *,
    baseline: Scorecard,
    candidate: Scorecard,
    max_dimension_regression: float = 0.05,
    max_slice_regression: float = 0.10,
    max_cost_increase: float = 0.20,
) -> RegressionVerdictPayload:
    failures: list[str] = []

    dimension_deltas: list[DimensionDelta] = []
    for dim in DIMENSIONS:
        b = float(getattr(baseline, dim))
        c = float(getattr(candidate, dim))
        delta = c - b
        # baseline em 1-5 → permitimos uma queda absoluta de (max_dim_regression × 5)
        threshold = max_dimension_regression * 5
        passed = delta >= -threshold
        if not passed:
            failures.append(
                f"dimensão '{dim}' caiu {delta:.2f} (limite -{threshold:.2f})"
            )
        dimension_deltas.append(
            DimensionDelta(
                dimension=dim, baseline=b, candidate=c, delta=delta, passed=passed
            )
        )

    slice_deltas: list[SliceDelta] = []
    a_slices = baseline.per_slice_breakdown or {}
    b_slices = candidate.per_slice_breakdown or {}
    for slice_name in sorted(set(a_slices) | set(b_slices)):
        a = float(a_slices.get(slice_name, {}).get("aggregate_score", 0.0))
        b = float(b_slices.get(slice_name, {}).get("aggregate_score", 0.0))
        delta = b - a
        # aqui o score já está em 0-1 → max_slice_regression é absoluto na escala 0-1
        passed = delta >= -max_slice_regression
        if not passed:
            failures.append(
                f"slice '{slice_name}' regrediu {delta:.3f} (limite -{max_slice_regression:.3f})"
            )
        slice_deltas.append(
            SliceDelta(
                slice=slice_name,
                baseline_score=a,
                candidate_score=b,
                delta=delta,
                passed=passed,
            )
        )

    cost_delta_pct = _pct_change(baseline.total_cost_usd, candidate.total_cost_usd)
    cost_passed = cost_delta_pct <= max_cost_increase
    if not cost_passed:
        failures.append(
            f"custo subiu {cost_delta_pct:.1%} (limite +{max_cost_increase:.1%})"
        )

    return RegressionVerdictPayload(
        passed=len(failures) == 0,
        failures=failures,
        dimension_deltas=dimension_deltas,
        slice_deltas=slice_deltas,
        cost_delta_pct=cost_delta_pct,
        cost_passed=cost_passed,
    )
