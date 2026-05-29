from __future__ import annotations

import re
from typing import Any

from app.evaluation.checks.registry import CheckResult, register
from app.evaluation.json_extract import extract_json_text


@register("regex_match")
def check(output: str, expected: dict[str, Any], config: dict[str, Any]) -> CheckResult:
    """
    Verifica se o output (ou um campo do JSON) bate com uma regex.

    Config:
      - pattern: str (obrigatório)
      - field: str | None — se informado, aplica ao campo do JSON; senão, ao output cru
      - flags: list[str] — "i" (IGNORECASE), "s" (DOTALL), "m" (MULTILINE)
      - mode: "search" (default) | "fullmatch"
      - negate: bool (default False) — se True, "passa" significa NÃO bater
    """
    import json

    pattern: str = config.get("pattern", "")
    if not pattern:
        return CheckResult(passed=False, score=0.0, detail="config.pattern não informado")

    flag_str = config.get("flags", [])
    flags = 0
    for f in flag_str:
        flags |= {"i": re.IGNORECASE, "s": re.DOTALL, "m": re.MULTILINE}.get(f.lower(), 0)

    target_text = output
    field = config.get("field")
    if field is not None:
        try:
            parsed = json.loads(extract_json_text(output))
        except json.JSONDecodeError:
            return CheckResult(passed=False, score=0.0, detail="JSON inválido")
        target_text = str(parsed.get(field, ""))

    regex = re.compile(pattern, flags)
    mode = config.get("mode", "search")
    matched = bool(regex.fullmatch(target_text) if mode == "fullmatch" else regex.search(target_text))

    negate = bool(config.get("negate", False))
    passed = (not matched) if negate else matched
    return CheckResult(
        passed=passed,
        score=1.0 if passed else 0.0,
        detail=f"pattern={pattern!r} matched={matched} negate={negate}",
    )
