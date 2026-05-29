"""
Smoke test dos adapters REAIS (Claude / OpenAI / Gemini).

Faz UMA chamada mínima por provider que tiver chave configurada no .env e
imprime: texto, tokens reais (do `usage` do provedor) e custo calculado pela
mesma `compute_cost_usd` usada no worker. Não toca no banco.

Objetivo: provar, com 1 chamada barata, que a integração real está de pé —
antes de gastar tokens num EvalRun inteiro.

Uso (dentro do container backend, ou com venv local + .env preenchido):
    python -m scripts.smoke_providers
    python -m scripts.smoke_providers --provider claude --provider openai

Custo: ~alguns tokens por provider (prompt minúsculo, max_tokens baixo).
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.adapters import get_adapter
from app.core.config import get_settings
from app.core.pricing import compute_cost_usd
from app.models.enums import Provider

# (provider, model_name, price_in/1M, price_out/1M) — pricing maio/2026, espelha o seed.
SMOKE_TARGETS: list[tuple[Provider, str, float, float]] = [
    (Provider.claude, "claude-haiku-4-5", 1.00, 5.00),
    (Provider.openai, "gpt-4o-mini", 0.15, 0.60),
]

SYSTEM = "You are a terse assistant. Reply with valid JSON only."
USER = 'Return a JSON object: {"ok": true, "provider_check": "<one short word>"}'


def _has_key(provider: Provider) -> bool:
    s = get_settings()
    return {
        Provider.claude: bool(s.anthropic_api_key),
        Provider.openai: bool(s.openai_api_key),
        Provider.gemini: bool(s.gemini_api_key),
        Provider.fake: True,
    }[provider]


async def _smoke_one(provider: Provider, model: str, p_in: float, p_out: float) -> bool:
    print(f"\n── {provider.value} / {model} ──")
    if not _has_key(provider):
        print(f"  ⊘ pulando: chave de API ausente no .env ({provider.value})")
        return True  # ausência de chave não é falha de teste

    adapter = get_adapter(provider, model)
    try:
        resp = await adapter.call(
            system=SYSTEM,
            user=USER,
            params={"temperature": 0.0, "max_tokens": 64},
        )
    except Exception as e:  # smoke test reporta qualquer falha do provedor
        print(f"  ✗ FALHA: {type(e).__name__}: {e}")
        return False

    cost = compute_cost_usd(resp.input_tokens, resp.output_tokens, p_in, p_out)
    print(f"  ✓ ok  latency={resp.latency_ms}ms")
    print(f"    tokens: in={resp.input_tokens} out={resp.output_tokens}")
    print(f"    custo: ${cost:.6f}")
    print(f"    texto: {resp.text[:160]!r}")
    return True


async def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test dos adapters reais")
    parser.add_argument(
        "--provider",
        action="append",
        choices=[p.value for p in Provider if p != Provider.fake],
        help="Limita a providers específicos (repetível). Default: todos com chave.",
    )
    args = parser.parse_args()

    targets = SMOKE_TARGETS
    if args.provider:
        wanted = set(args.provider)
        targets = [t for t in SMOKE_TARGETS if t[0].value in wanted]

    print("== Smoke test — adapters reais ==")
    results = [await _smoke_one(*t) for t in targets]
    ok = all(results)
    print(f"\n== {'TODOS OK' if ok else 'FALHAS DETECTADAS'} ==")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
