from __future__ import annotations

import json
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaError

from app.evaluation.checks.registry import CheckResult, register
from app.evaluation.json_extract import extract_json_text


@register("json_schema_valid")
def check(output: str, expected: dict[str, Any], config: dict[str, Any]) -> CheckResult:
    """
    Verifica se `output` parseia como JSON e (opcionalmente) valida contra um schema.

    Config:
      - schema: dict (JSON Schema Draft 2020-12). Se ausente, valida só parse JSON.
    """
    schema = config.get("schema")
    try:
        parsed = json.loads(extract_json_text(output))
    except json.JSONDecodeError as e:
        return CheckResult(passed=False, score=0.0, detail=f"JSON inválido: {e}")

    if schema is None:
        return CheckResult(passed=True, score=1.0, detail="JSON parse OK (sem schema)")

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(parsed), key=lambda e: e.path)
    if errors:
        first: JsonSchemaError = errors[0]
        path = ".".join(str(p) for p in first.absolute_path) or "<root>"
        return CheckResult(
            passed=False, score=0.0, detail=f"schema falhou em '{path}': {first.message}"
        )
    return CheckResult(passed=True, score=1.0, detail="schema OK")
