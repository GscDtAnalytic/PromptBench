"""
Registry de checks determinísticos.

Cada check é uma função pura:
    check(output: str, expected: dict, config: dict) -> CheckResult

Adicionar um check novo = criar a função + registrar com `@register("nome")`.
Nenhum estado externo, nenhum I/O, nenhuma chamada a LLM. Testável trivialmente.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CheckResult:
    passed: bool
    score: float  # 0.0 a 1.0
    detail: str = ""


@dataclass
class CheckSpec:
    """Especificação que vem de prompt/test_case config para escolher e parametrizar checks."""

    name: str
    config: dict[str, Any] = field(default_factory=dict)
    required: bool = True  # se True e falhar, EvalResult.passed = False


CheckFn = Callable[[str, dict[str, Any], dict[str, Any]], CheckResult]

_REGISTRY: dict[str, CheckFn] = {}


def register(name: str) -> Callable[[CheckFn], CheckFn]:
    def decorator(fn: CheckFn) -> CheckFn:
        if name in _REGISTRY:
            raise ValueError(f"check '{name}' já registrado")
        _REGISTRY[name] = fn
        return fn

    return decorator


def run_check(
    name: str, output: str, expected: dict[str, Any], config: dict[str, Any] | None = None
) -> CheckResult:
    if name not in _REGISTRY:
        raise KeyError(f"check '{name}' não registrado. Disponíveis: {sorted(_REGISTRY)}")
    return _REGISTRY[name](output, expected, config or {})


def run_checks(
    specs: list[CheckSpec], output: str, expected: dict[str, Any]
) -> dict[str, CheckResult]:
    """Executa uma lista de checks e retorna {check_name: CheckResult}."""
    return {spec.name: run_check(spec.name, output, expected, spec.config) for spec in specs}


def list_checks() -> list[str]:
    return sorted(_REGISTRY)


# Importa os checks para popular o registry (efeito colateral de import)
from app.evaluation.checks import (  # noqa: E402, F401
    exact_match,
    json_schema_valid,
    numeric_range,
    regex_match,
    required_fields,
    set_match,
)
