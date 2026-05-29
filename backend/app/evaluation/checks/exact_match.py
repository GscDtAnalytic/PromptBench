from __future__ import annotations

import json
from typing import Any

from app.evaluation.checks.registry import CheckResult, register
from app.evaluation.json_extract import extract_json_text


@register("exact_match")
def check(output: str, expected: dict[str, Any], config: dict[str, Any]) -> CheckResult:
    """
    Verifica match exato de um campo do output contra o expected.

    Config:
      - field: str — campo a comparar (no JSON output e em expected)
      - case_sensitive: bool (default True)
    """
    field: str = config.get("field", "")
    case_sensitive: bool = bool(config.get("case_sensitive", True))

    if not field:
        return CheckResult(passed=False, score=0.0, detail="config.field não informado")

    try:
        parsed = json.loads(extract_json_text(output))
    except json.JSONDecodeError:
        return CheckResult(passed=False, score=0.0, detail="JSON inválido")

    actual = parsed.get(field)
    target = expected.get(field)

    if actual is None or target is None:
        return CheckResult(
            passed=False, score=0.0, detail=f"campo '{field}' ausente em output ou expected"
        )

    if isinstance(actual, str) and isinstance(target, str) and not case_sensitive:
        passed = actual.lower() == target.lower()
    else:
        passed = actual == target

    return CheckResult(
        passed=passed,
        score=1.0 if passed else 0.0,
        detail=f"{field}: actual={actual!r} vs expected={target!r}",
    )
