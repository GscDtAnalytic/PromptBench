from __future__ import annotations

import json
from typing import Any

from app.evaluation.checks.registry import CheckResult, register
from app.evaluation.json_extract import extract_json_text


@register("set_match")
def check(output: str, expected: dict[str, Any], config: dict[str, Any]) -> CheckResult:
    """
    Compara dois campos como conjuntos (ordem não importa). Útil para `matched_skills` etc.

    Config:
      - field: str
      - case_sensitive: bool (default False)
      - score_mode: "jaccard" (default) | "binary"
    """
    field: str = config.get("field", "")
    case_sensitive: bool = bool(config.get("case_sensitive", False))
    score_mode: str = config.get("score_mode", "jaccard")

    if not field:
        return CheckResult(passed=False, score=0.0, detail="config.field não informado")

    try:
        parsed = json.loads(extract_json_text(output))
    except json.JSONDecodeError:
        return CheckResult(passed=False, score=0.0, detail="JSON inválido")

    actual = parsed.get(field, [])
    target = expected.get(field, [])

    if not isinstance(actual, list) or not isinstance(target, list):
        return CheckResult(passed=False, score=0.0, detail=f"campo '{field}' não é lista")

    def norm(items: list[Any]) -> set[str]:
        if case_sensitive:
            return {str(i) for i in items}
        return {str(i).lower() for i in items}

    actual_set = norm(actual)
    target_set = norm(target)

    if not target_set and not actual_set:
        return CheckResult(passed=True, score=1.0, detail="ambos vazios")

    intersection = actual_set & target_set
    union = actual_set | target_set
    jaccard = len(intersection) / len(union) if union else 1.0

    if score_mode == "binary":
        passed = actual_set == target_set
        return CheckResult(
            passed=passed,
            score=1.0 if passed else 0.0,
            detail=f"binary: actual={sorted(actual_set)} target={sorted(target_set)}",
        )

    passed = jaccard >= float(config.get("min_jaccard", 1.0))
    return CheckResult(
        passed=passed,
        score=jaccard,
        detail=f"jaccard={jaccard:.2f} (∩={len(intersection)}, ∪={len(union)})",
    )
