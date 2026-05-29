from __future__ import annotations

import json
from typing import Any

from app.evaluation.checks.registry import CheckResult, register
from app.evaluation.json_extract import extract_json_text


@register("required_fields_present")
def check(output: str, expected: dict[str, Any], config: dict[str, Any]) -> CheckResult:
    """
    Verifica se todos os campos em `config.fields` estão presentes no JSON do output.

    Config:
      - fields: list[str] — chaves obrigatórias (top-level)
    """
    fields: list[str] = list(config.get("fields", []))
    if not fields:
        return CheckResult(passed=True, score=1.0, detail="sem campos requeridos")

    try:
        parsed = json.loads(extract_json_text(output))
    except json.JSONDecodeError:
        return CheckResult(passed=False, score=0.0, detail="JSON inválido")

    if not isinstance(parsed, dict):
        return CheckResult(passed=False, score=0.0, detail="output não é objeto JSON")

    missing = [f for f in fields if f not in parsed]
    if missing:
        return CheckResult(
            passed=False,
            score=(len(fields) - len(missing)) / len(fields),
            detail=f"faltam campos: {missing}",
        )
    return CheckResult(passed=True, score=1.0, detail="todos os campos presentes")
