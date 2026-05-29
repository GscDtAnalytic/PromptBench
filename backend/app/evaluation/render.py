from __future__ import annotations

from typing import Any


def render_template(template: str, variables: dict[str, Any]) -> str:
    """
    Renderiza template via `str.format_map`, tolerando chaves ausentes.

    Decisão: prompts usam `{var}` simples. Sem Jinja para manter o domínio pequeno e
    auditável. Se faltar uma variável, substitui por "" — o judge marca como falha
    se o output for sem contexto.
    """

    class _Missing(dict[str, Any]):
        def __missing__(self, key: str) -> str:
            return ""

    safe_vars = _Missing()
    safe_vars.update({k: ("" if v is None else v) for k, v in variables.items()})
    return template.format_map(safe_vars)
