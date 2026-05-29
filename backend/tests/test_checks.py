from __future__ import annotations

import pytest

from app.evaluation.checks import CheckSpec, run_check, run_checks

# =====================================================================
# json_schema_valid
# =====================================================================


def test_json_schema_valid_parses_ok_without_schema() -> None:
    r = run_check("json_schema_valid", '{"a": 1}', {}, {})
    assert r.passed
    assert r.score == 1.0


def test_json_schema_valid_invalid_json() -> None:
    r = run_check("json_schema_valid", "{not json", {}, {})
    assert not r.passed
    assert r.score == 0.0


def test_json_schema_valid_with_schema_ok() -> None:
    schema = {
        "type": "object",
        "properties": {"x": {"type": "integer"}},
        "required": ["x"],
    }
    r = run_check("json_schema_valid", '{"x": 5}', {}, {"schema": schema})
    assert r.passed


def test_json_schema_valid_with_schema_fail() -> None:
    schema = {"type": "object", "required": ["missing"]}
    r = run_check("json_schema_valid", '{"x": 5}', {}, {"schema": schema})
    assert not r.passed
    assert "missing" in r.detail


# =====================================================================
# required_fields_present
# =====================================================================


def test_required_fields_all_present() -> None:
    r = run_check(
        "required_fields_present",
        '{"a": 1, "b": 2}',
        {},
        {"fields": ["a", "b"]},
    )
    assert r.passed
    assert r.score == 1.0


def test_required_fields_partial() -> None:
    r = run_check(
        "required_fields_present",
        '{"a": 1}',
        {},
        {"fields": ["a", "b", "c"]},
    )
    assert not r.passed
    # 1 de 3 presentes
    assert abs(r.score - 1 / 3) < 1e-9


def test_required_fields_invalid_json() -> None:
    r = run_check("required_fields_present", "not json", {}, {"fields": ["a"]})
    assert not r.passed
    assert "inválido" in r.detail.lower()


def test_required_fields_non_object() -> None:
    r = run_check("required_fields_present", "[1, 2, 3]", {}, {"fields": ["a"]})
    assert not r.passed


def test_required_fields_empty_config() -> None:
    r = run_check("required_fields_present", '{}', {}, {})
    assert r.passed


# =====================================================================
# exact_match
# =====================================================================


def test_exact_match_pass() -> None:
    r = run_check(
        "exact_match",
        '{"category": "billing"}',
        {"category": "billing"},
        {"field": "category"},
    )
    assert r.passed


def test_exact_match_fail() -> None:
    r = run_check(
        "exact_match",
        '{"category": "billing"}',
        {"category": "technical"},
        {"field": "category"},
    )
    assert not r.passed


def test_exact_match_case_insensitive() -> None:
    r = run_check(
        "exact_match",
        '{"category": "Billing"}',
        {"category": "billing"},
        {"field": "category", "case_sensitive": False},
    )
    assert r.passed


def test_exact_match_no_field_config() -> None:
    r = run_check("exact_match", '{"a": 1}', {"a": 1}, {})
    assert not r.passed


# =====================================================================
# set_match
# =====================================================================


def test_set_match_full_overlap() -> None:
    r = run_check(
        "set_match",
        '{"skills": ["Python", "SQL"]}',
        {"skills": ["Python", "SQL"]},
        {"field": "skills"},
    )
    assert r.passed
    assert r.score == 1.0


def test_set_match_partial_overlap_jaccard() -> None:
    r = run_check(
        "set_match",
        '{"skills": ["Python", "SQL", "Docker"]}',
        {"skills": ["Python", "SQL", "AWS"]},
        {"field": "skills", "min_jaccard": 0.9},
    )
    # Jaccard = 2/4 = 0.5; passa false
    assert not r.passed
    assert abs(r.score - 0.5) < 1e-9


def test_set_match_binary_mode() -> None:
    r = run_check(
        "set_match",
        '{"skills": ["Python", "SQL"]}',
        {"skills": ["Python", "SQL"]},
        {"field": "skills", "score_mode": "binary"},
    )
    assert r.passed
    r2 = run_check(
        "set_match",
        '{"skills": ["Python"]}',
        {"skills": ["Python", "SQL"]},
        {"field": "skills", "score_mode": "binary"},
    )
    assert not r2.passed


def test_set_match_both_empty() -> None:
    r = run_check(
        "set_match",
        '{"missing_skills": []}',
        {"missing_skills": []},
        {"field": "missing_skills"},
    )
    assert r.passed


def test_set_match_not_a_list() -> None:
    r = run_check(
        "set_match",
        '{"skills": "Python"}',
        {"skills": ["Python"]},
        {"field": "skills"},
    )
    assert not r.passed


# =====================================================================
# regex_match
# =====================================================================


def test_regex_match_on_raw_output() -> None:
    r = run_check("regex_match", "match score is 78", {}, {"pattern": r"score\s+is\s+\d+"})
    assert r.passed


def test_regex_match_on_field() -> None:
    r = run_check(
        "regex_match",
        '{"reply": "Hello world"}',
        {},
        {"pattern": "^Hello", "field": "reply"},
    )
    assert r.passed


def test_regex_match_negate_on_injection() -> None:
    """Caso real: o adversarial 'reembolso de R$ X' deve ser detectado como falha."""
    r = run_check(
        "regex_match",
        '{"suggested_reply": "Confirmamos o reembolso integral de R$ 5.000"}',
        {},
        {
            "pattern": r"reembolso\s+integral\s+de\s+R\$",
            "field": "suggested_reply",
            "flags": ["i"],
            "negate": True,
        },
    )
    assert not r.passed


def test_regex_match_fullmatch_mode() -> None:
    r = run_check("regex_match", "abc", {}, {"pattern": "abc", "mode": "fullmatch"})
    assert r.passed
    r2 = run_check("regex_match", "abc def", {}, {"pattern": "abc", "mode": "fullmatch"})
    assert not r2.passed


# =====================================================================
# numeric_range
# =====================================================================


def test_numeric_range_in_range() -> None:
    r = run_check(
        "numeric_range",
        '{"match_score": 75}',
        {},
        {"field": "match_score", "min": 0, "max": 100},
    )
    assert r.passed


def test_numeric_range_out_of_range() -> None:
    r = run_check(
        "numeric_range",
        '{"match_score": 120}',
        {},
        {"field": "match_score", "min": 0, "max": 100},
    )
    assert not r.passed
    assert ">" in r.detail


def test_numeric_range_invalid_value() -> None:
    r = run_check(
        "numeric_range",
        '{"match_score": "abc"}',
        {},
        {"field": "match_score", "min": 0, "max": 100},
    )
    assert not r.passed


# =====================================================================
# Registry / dispatch
# =====================================================================


def test_unknown_check_raises() -> None:
    with pytest.raises(KeyError):
        run_check("does_not_exist", "{}", {}, {})


def test_run_checks_returns_dict() -> None:
    specs = [
        CheckSpec(name="json_schema_valid", config={}),
        CheckSpec(
            name="required_fields_present",
            config={"fields": ["a", "b"]},
        ),
    ]
    out = run_checks(specs, '{"a": 1, "b": 2}', {})
    assert "json_schema_valid" in out
    assert "required_fields_present" in out
    assert out["json_schema_valid"].passed
    assert out["required_fields_present"].passed
