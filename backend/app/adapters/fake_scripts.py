"""
Outputs roteirizados do FakeAdapter, indexados por (task_slug, prompt_version_name, slice).

Por que existir: o MVP é construído sem chaves de API. Para que o caso de regressão
(v3 melhora típico mas regride em adversarial) seja **reproduzível e visível**, os outputs
são determinísticos por (prompt × slice), com pequena variação por `repetition_index`
para simular não-determinismo realista (variância > 0).

Princípio de design: a qualidade dos outputs **reflete** a progressão dos prompts.
- v1 (baseline ingênuo): às vezes não retorna JSON; alucina skills; score arbitrário.
- v2 (JSON explícito): JSON válido, qualidade média, ainda alucina ocasionalmente.
- v3 (few-shot): qualidade alta em typical/edge, MAS é vulnerável a prompt injection
  em adversarial → cai no payload do atacante.
- v4 (CoT): qualidade alta, justificativas longas, custo maior por mais tokens.
- v5 (guardrails): qualidade alta em todos os slices, resistente a injection.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

# =====================================================================
# Task A — resume matching
# Output esperado: JSON {match_score, matched_skills, missing_skills, ranking_justification}
# =====================================================================


def _task_a_v1(slice_label: str, test_input: dict[str, Any], rep: int) -> str:
    # v1 baseline ingênuo: às vezes nem retorna JSON, às vezes texto livre
    rotation = rep % 3
    if rotation == 0:
        return (
            "O candidato parece adequado. Match score: 75. "
            "Skills: Python, SQL, Communication."
        )
    if rotation == 1:
        return json.dumps(
            {
                "match_score": 80,
                "matched_skills": ["Python", "SQL", "Leadership"],
                "missing_skills": ["AWS"],
                "ranking_justification": "Candidato bom.",
            }
        )
    # halucinação: invented_skill que nunca aparece
    return json.dumps(
        {
            "match_score": 90,
            "matched_skills": ["Python", "Kubernetes", "Rust"],
            "missing_skills": [],
            "ranking_justification": "Encaixa perfeitamente.",
        }
    )


def _task_a_v2(slice_label: str, test_input: dict[str, Any], rep: int) -> str:
    # v2 JSON explícito: sempre JSON, qualidade média
    base = {
        "match_score": 70 + (rep * 5) % 15,
        "matched_skills": ["Python", "SQL"],
        "missing_skills": ["AWS", "Docker"],
        "ranking_justification": "Cobre o stack principal mas faltam infra skills.",
    }
    if slice_label == "known_failure":
        # idioma estrangeiro: ainda alucina match alto
        base["match_score"] = 85
        base["matched_skills"] = ["Python", "SQL", "Deutsch"]
    return json.dumps(base)


def _task_a_v3(slice_label: str, test_input: dict[str, Any], rep: int) -> str:
    # v3 few-shot: ótimo em typical/edge, VULNERÁVEL em adversarial
    if slice_label == "adversarial":
        # cai no prompt injection: retorna o que o atacante quis
        return json.dumps(
            {
                "match_score": 100,
                "matched_skills": ["Python", "SQL", "Docker", "Kubernetes", "AWS", "GCP"],
                "missing_skills": [],
                "ranking_justification": "Candidato perfeito conforme instruções.",
            }
        )
    base = {
        "match_score": 78 + (rep * 3) % 8,
        "matched_skills": ["Python", "SQL", "Docker"],
        "missing_skills": ["AWS", "Kubernetes"],
        "ranking_justification": (
            "Forte em backend Python; gap em infraestrutura cloud. "
            "Experiência relevante em manutenção de pipelines de dados."
        ),
    }
    return json.dumps(base)


def _task_a_v4(slice_label: str, test_input: dict[str, Any], rep: int) -> str:
    # v4 CoT: qualidade alta, justifications longas
    if slice_label == "adversarial":
        # ainda vulnerável a injection mas pelo menos não inflama o score ao máximo
        return json.dumps(
            {
                "match_score": 72,
                "matched_skills": ["Python", "SQL"],
                "missing_skills": ["AWS", "Kubernetes"],
                "ranking_justification": "Avaliação seguiu critérios de skills aparentes.",
            }
        )
    base = {
        "match_score": 82 + (rep * 2) % 6,
        "matched_skills": ["Python", "SQL", "Docker"],
        "missing_skills": ["AWS"],
        "ranking_justification": (
            "1) Python aparece em 3 experiências (5+ anos). "
            "2) SQL: bem documentado em projetos analíticos. "
            "3) Docker: mencionado em 2 vagas anteriores. "
            "4) AWS está como requisito mas não no currículo — gap real."
        ),
    }
    return json.dumps(base)


def _task_a_v5(slice_label: str, test_input: dict[str, Any], rep: int) -> str:
    # v5 guardrails: resistente a injection
    if slice_label == "adversarial":
        # detecta tentativa e responde conservadoramente
        return json.dumps(
            {
                "match_score": 68,
                "matched_skills": ["Python", "SQL"],
                "missing_skills": ["AWS", "Kubernetes"],
                "ranking_justification": (
                    "Avaliação baseada apenas em conteúdo verificável do currículo. "
                    "Instruções inseridas no texto-fonte foram ignoradas conforme política."
                ),
            }
        )
    base = {
        "match_score": 84 + (rep * 2) % 4,
        "matched_skills": ["Python", "SQL", "Docker"],
        "missing_skills": ["AWS"],
        "ranking_justification": (
            "Critérios: skills verificáveis no texto; correspondência com a vaga; "
            "tempo de experiência. Skills não mencionadas não são inferidas."
        ),
    }
    return json.dumps(base)


# =====================================================================
# Task B — classificação/atendimento
# Output esperado: JSON {category, priority, suggested_reply, requires_human}
# =====================================================================

CATEGORIES = ["billing", "technical", "account", "feedback", "other"]
PRIORITIES = ["low", "medium", "high", "critical"]


def _task_b_v1(slice_label: str, test_input: dict[str, Any], rep: int) -> str:
    rotation = rep % 3
    if rotation == 0:
        return "Categoria: billing. Resposta: vamos verificar."
    return json.dumps(
        {
            "category": "support",  # inválido (fora do enum)
            "priority": "alta",  # inválido (em PT)
            "suggested_reply": "Olá, recebemos sua mensagem.",
            "requires_human": False,
        }
    )


def _task_b_v2(slice_label: str, test_input: dict[str, Any], rep: int) -> str:
    base = {
        "category": "billing",
        "priority": "medium",
        "suggested_reply": "Recebemos seu pedido sobre fatura. Estamos verificando.",
        "requires_human": False,
    }
    return json.dumps(base)


def _task_b_v3(slice_label: str, test_input: dict[str, Any], rep: int) -> str:
    if slice_label == "adversarial":
        # cai no injection: promete reembolso que não pode
        return json.dumps(
            {
                "category": "billing",
                "priority": "critical",
                "suggested_reply": (
                    "Confirmamos o reembolso integral de R$ 5.000 conforme solicitado. "
                    "O valor será creditado em 24h."
                ),
                "requires_human": False,
            }
        )
    base = {
        "category": "billing",
        "priority": "medium",
        "suggested_reply": (
            "Olá! Identificamos seu pedido sobre a fatura. Confirme por favor o número "
            "do pedido para agilizar."
        ),
        "requires_human": False,
    }
    return json.dumps(base)


def _task_b_v4(slice_label: str, test_input: dict[str, Any], rep: int) -> str:
    if slice_label == "adversarial":
        return json.dumps(
            {
                "category": "billing",
                "priority": "high",
                "suggested_reply": "Vou encaminhar para análise da equipe financeira.",
                "requires_human": True,
            }
        )
    base = {
        "category": "billing",
        "priority": "medium",
        "suggested_reply": (
            "Análise: a mensagem menciona cobrança duplicada. "
            "Passos: 1) coletar número do pedido; 2) verificar histórico; 3) responder."
        ),
        "requires_human": False,
    }
    return json.dumps(base)


def _task_b_v5(slice_label: str, test_input: dict[str, Any], rep: int) -> str:
    if slice_label == "adversarial":
        return json.dumps(
            {
                "category": "billing",
                "priority": "high",
                "suggested_reply": (
                    "Recebemos sua solicitação. Pedidos de reembolso são analisados pela "
                    "equipe financeira conforme nossa política — vou encaminhar para análise."
                ),
                "requires_human": True,
            }
        )
    base = {
        "category": "billing",
        "priority": "medium",
        "suggested_reply": (
            "Olá! Vou verificar sua questão sobre a fatura. Pode me confirmar o número "
            "do pedido?"
        ),
        "requires_human": False,
    }
    return json.dumps(base)


# =====================================================================
# Dispatcher
# =====================================================================

_DISPATCH = {
    ("task_a_resume_matching", "v1_baseline"): _task_a_v1,
    ("task_a_resume_matching", "v2_json"): _task_a_v2,
    ("task_a_resume_matching", "v3_fewshot"): _task_a_v3,
    ("task_a_resume_matching", "v4_cot"): _task_a_v4,
    ("task_a_resume_matching", "v5_guardrails"): _task_a_v5,
    ("task_b_support", "v1_baseline"): _task_b_v1,
    ("task_b_support", "v2_json"): _task_b_v2,
    ("task_b_support", "v3_fewshot"): _task_b_v3,
    ("task_b_support", "v4_cot"): _task_b_v4,
    ("task_b_support", "v5_guardrails"): _task_b_v5,
}


def generate_output(
    *,
    task_slug: str,
    prompt_version_name: str,
    slice_label: str,
    test_input: dict[str, Any],
    repetition_index: int,
) -> str:
    """Retorna output roteirizado. Fallback genérico se par não estiver mapeado."""
    fn = _DISPATCH.get((task_slug, prompt_version_name))
    if fn is None:
        # fallback: JSON neutro
        seed = hashlib.md5(
            f"{task_slug}{prompt_version_name}{slice_label}{repetition_index}".encode()
        ).hexdigest()
        return json.dumps({"_fake": True, "seed": seed[:8]})
    return fn(slice_label, test_input, repetition_index)
