"""
Cálculo de custo a partir de (input_tokens, output_tokens) × pricing.

NUNCA hardcode pricing nos adapters. A fonte de verdade é o `ModelConfig.price_per_1m_*`
persistido no banco. Esta função existe para garantir que o cálculo é uniforme entre
todos os adapters (fake e reais).
"""

from __future__ import annotations

from decimal import Decimal


def compute_cost_usd(
    input_tokens: int,
    output_tokens: int,
    price_per_1m_input: float,
    price_per_1m_output: float,
) -> float:
    """Retorna custo em USD com 6 casas decimais (precisão suficiente para LLMOps)."""
    input_cost = Decimal(str(input_tokens)) * Decimal(str(price_per_1m_input)) / Decimal("1000000")
    output_cost = (
        Decimal(str(output_tokens)) * Decimal(str(price_per_1m_output)) / Decimal("1000000")
    )
    return float((input_cost + output_cost).quantize(Decimal("0.000001")))
