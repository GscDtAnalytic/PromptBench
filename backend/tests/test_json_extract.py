"""Testes do extrator de JSON robusto (gap real-vs-fake: cercas markdown + CoT)."""

from __future__ import annotations

import json

import pytest

from app.evaluation.json_extract import extract_json_text


def _loads(raw: str) -> dict:
    return json.loads(extract_json_text(raw))


def test_json_limpo_passa_inalterado() -> None:
    assert _loads('{"a": 1, "b": "x"}') == {"a": 1, "b": "x"}


def test_cercas_markdown_json() -> None:
    raw = '```json\n{"category": "billing", "priority": "high"}\n```'
    assert _loads(raw) == {"category": "billing", "priority": "high"}


def test_cercas_sem_lang() -> None:
    assert _loads('```\n{"ok": true}\n```') == {"ok": True}


def test_cot_prosa_antes_do_json_cercado() -> None:
    # Caso real observado com claude-haiku em prompt CoT.
    raw = (
        "**Raciocínio interno:**\n"
        "1. Problema: cobrança duplicada\n"
        "2. Categoria: billing\n\n"
        "**Resposta:**\n\n"
        '```json\n{"category": "billing", "requires_human": true}\n```'
    )
    assert _loads(raw) == {"category": "billing", "requires_human": True}


def test_prosa_com_objeto_nu_sem_cercas() -> None:
    raw = 'Aqui está a resposta: {"match_score": 80, "matched_skills": ["py"]} pronto.'
    assert _loads(raw) == {"match_score": 80, "matched_skills": ["py"]}


def test_pega_ultimo_bloco_cercado() -> None:
    raw = '```json\n{"draft": 1}\n```\nrevisado:\n```json\n{"final": 2}\n```'
    assert _loads(raw) == {"final": 2}


def test_array_json() -> None:
    assert json.loads(extract_json_text("resultado: [1, 2, 3]")) == [1, 2, 3]


def test_texto_sem_json_devolve_cru_e_falha_no_loads() -> None:
    # Sem JSON reconhecível: devolve o texto cru → json.loads do chamador falha.
    out = extract_json_text("não há json aqui")
    assert out == "não há json aqui"
    with pytest.raises(json.JSONDecodeError):
        json.loads(out)


def test_vazio_e_none() -> None:
    assert extract_json_text("") == ""
    assert extract_json_text(None) == ""
