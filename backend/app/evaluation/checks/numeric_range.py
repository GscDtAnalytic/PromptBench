from __future__ import annotations

import json
from typing import Any

from app.evaluation.checks.registry import CheckResult, register
from app.evaluation.json_extract import extract_json_text


@register("numeric_range")
def check(output: str, expected: dict[str, Any], config: dict[str, Any]) -> CheckResult:
    """
    Verifica se um valor numérico do JSON está num intervalo permitido.

    Config:
      - field: str (obrigatório)
      - min: float | None
      - max: float | None
    """
    field: str = config.get("field", "")
    if not field:
        return CheckResult(passed=False, score=0.0, detail="config.field não informado")

    try:
        parsed = json.loads(extract_json_text(output))
    except json.JSONDecodeError:
        return CheckResult(passed=False, score=0.0, detail="JSON inválido")

    value = parsed.get(field)
    if value is None:
        return CheckResult(passed=False, score=0.0, detail=f"campo '{field}' ausente")
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return CheckResult(passed=False, score=0.0, detail=f"campo '{field}' não numérico")

    lo = config.get("min")
    hi = config.get("max")
    if lo is not None and numeric < float(lo):
        return CheckResult(
            passed=False, score=0.0, detail=f"{field}={numeric} < min={lo}"
        )
    if hi is not None and numeric > float(hi):
        return CheckResult(
            passed=False, score=0.0, detail=f"{field}={numeric} > max={hi}"
        )
    return CheckResult(passed=True, score=1.0, detail=f"{field}={numeric} dentro de [{lo}, {hi}]")
