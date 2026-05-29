"""
Agregação de EvalResults em Scorecard.

Função pura: recebe uma lista de "resultados normalizados" (dataclass abaixo) e devolve
um payload do Scorecard. NÃO toca em DB. Isso a torna trivialmente testável.

Regras (CLAUDE.md):
- score agregado nunca esconde regressão de slice → SEMPRE quebrar por slice.
- variância é métrica de 1ª classe (sobre repetições do mesmo test_case).
- pesos das 4 dimensões dependem do task_type:
    structured_extraction: factual/struct é o que mais importa
    classification_response: tone e adherence pesam mais
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from app.models.enums import SliceLabel, TaskType


@dataclass
class EvalResultRecord:
    """Snapshot normalizado de uma EvalResult — não amarra ao SQLAlchemy."""

    test_case_id: int
    slice: SliceLabel
    repetition_index: int
    passed: bool
    deterministic_scores: dict[str, dict[str, Any]] = field(default_factory=dict)
    rubric_scores: dict[str, Any] = field(default_factory=dict)
    latency_ms: int | None = None
    cost_usd: float | None = None


@dataclass
class ScorecardPayload:
    aggregate_score: float
    quality: float
    instruction_adherence: float
    factual_structural: float
    tone_format: float
    avg_latency_ms: float
    total_cost_usd: float
    failure_rate: float
    variance: float
    per_slice_breakdown: dict[str, dict[str, float]]


# Pesos por task_type — somam 1.0.
WEIGHTS: dict[TaskType, dict[str, float]] = {
    TaskType.structured_extraction: {
        "quality": 0.20,
        "instruction_adherence": 0.30,
        "factual_structural": 0.40,
        "tone_format": 0.10,
    },
    TaskType.classification_response: {
        "quality": 0.20,
        "instruction_adherence": 0.30,
        "factual_structural": 0.20,
        "tone_format": 0.30,
    },
}


def _rubric_dim_avg(records: list[EvalResultRecord], dim: str) -> float:
    """Média de uma dimensão da rubrica em 1-5, ignorando judge_error e None."""
    values: list[float] = []
    for r in records:
        rs = r.rubric_scores or {}
        if "judge_error" in rs:
            continue
        v = rs.get(dim)
        if v is None:
            continue
        try:
            values.append(float(v))
        except (TypeError, ValueError):
            continue
    return sum(values) / len(values) if values else 0.0


def _score_for_record(record: EvalResultRecord, weights: dict[str, float]) -> float:
    """
    Score 0-1 de uma EvalResult:
      - se passed=False → 0.0 (gate dos checks determinísticos)
      - senão: weighted avg das 4 dimensões da rubrica, normalizado de 1-5 para 0-1
    """
    if not record.passed:
        return 0.0
    rs = record.rubric_scores or {}
    if "judge_error" in rs:
        return 0.0
    total = 0.0
    for dim, w in weights.items():
        v = rs.get(dim)
        if v is None:
            return 0.0
        total += float(v) * w
    # 1-5 → 0-1
    return (total - 1.0) / 4.0


def _per_test_case_variance(records: list[EvalResultRecord], weights: dict[str, float]) -> float:
    """
    Desvio padrão amostral médio entre repetições do mesmo test_case.
    Mede quão não-determinístico é o (prompt × modelo) sobre o mesmo input.
    """
    by_case: dict[int, list[float]] = {}
    for r in records:
        by_case.setdefault(r.test_case_id, []).append(_score_for_record(r, weights))

    stdevs = []
    for scores in by_case.values():
        if len(scores) < 2:
            continue
        mean = sum(scores) / len(scores)
        var = sum((s - mean) ** 2 for s in scores) / (len(scores) - 1)
        stdevs.append(math.sqrt(var))

    return sum(stdevs) / len(stdevs) if stdevs else 0.0


def aggregate(
    records: list[EvalResultRecord], task_type: TaskType
) -> ScorecardPayload:
    if not records:
        return ScorecardPayload(
            aggregate_score=0.0,
            quality=0.0,
            instruction_adherence=0.0,
            factual_structural=0.0,
            tone_format=0.0,
            avg_latency_ms=0.0,
            total_cost_usd=0.0,
            failure_rate=0.0,
            variance=0.0,
            per_slice_breakdown={},
        )

    weights = WEIGHTS[task_type]

    # média ponderada das dimensões (1-5 normalizada não é feita aqui — reportamos 1-5)
    quality = _rubric_dim_avg(records, "quality")
    adherence = _rubric_dim_avg(records, "instruction_adherence")
    factual = _rubric_dim_avg(records, "factual_structural")
    tone = _rubric_dim_avg(records, "tone_format")

    scores = [_score_for_record(r, weights) for r in records]
    aggregate_score = sum(scores) / len(scores)

    latencies = [r.latency_ms for r in records if r.latency_ms is not None]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    costs = [r.cost_usd for r in records if r.cost_usd is not None]
    total_cost = sum(costs)

    failures = sum(1 for r in records if not r.passed)
    failure_rate = failures / len(records)

    variance = _per_test_case_variance(records, weights)

    # breakdown por slice
    by_slice: dict[str, list[EvalResultRecord]] = {}
    for r in records:
        by_slice.setdefault(r.slice.value, []).append(r)

    breakdown: dict[str, dict[str, float]] = {}
    for slice_name, slice_records in by_slice.items():
        slice_scores = [_score_for_record(r, weights) for r in slice_records]
        slice_failures = sum(1 for r in slice_records if not r.passed)
        breakdown[slice_name] = {
            "aggregate_score": sum(slice_scores) / len(slice_scores),
            "quality": _rubric_dim_avg(slice_records, "quality"),
            "instruction_adherence": _rubric_dim_avg(slice_records, "instruction_adherence"),
            "factual_structural": _rubric_dim_avg(slice_records, "factual_structural"),
            "tone_format": _rubric_dim_avg(slice_records, "tone_format"),
            "failure_rate": slice_failures / len(slice_records),
            "count": float(len(slice_records)),
        }

    return ScorecardPayload(
        aggregate_score=aggregate_score,
        quality=quality,
        instruction_adherence=adherence,
        factual_structural=factual,
        tone_format=tone,
        avg_latency_ms=avg_latency,
        total_cost_usd=total_cost,
        failure_rate=failure_rate,
        variance=variance,
        per_slice_breakdown=breakdown,
    )
