# Bloco 4 — Camada de avaliação (checks + judge + aggregate) + testes

## O que foi feito

### `app/evaluation/checks/` — 6 checks puros e testáveis

- **`registry.py`**: `CheckResult(passed, score, detail)`, `CheckSpec(name, config,
  required)`, `register()` decorator, `run_check()`, `run_checks()`. Cada check
  é função pura `(output, expected, config) -> CheckResult`.
- **`json_schema_valid.py`**: parse JSON + (opcional) validação Draft 2020-12.
- **`required_fields_present.py`**: top-level fields presentes; score parcial = ratio.
- **`exact_match.py`**: igualdade em campo do JSON; suporta `case_sensitive`.
- **`set_match.py`**: comparação Jaccard ou binary entre listas; case-insensitive default.
- **`regex_match.py`**: regex em output bruto ou campo do JSON; flags `i/s/m`;
  `mode=fullmatch|search`; `negate=True` (útil para detectar prompt injection).
- **`numeric_range.py`**: min/max em campo numérico do JSON.

### `app/evaluation/judge.py` — RubricJudge tipado (estilo DSPy)

- `RubricInputs(task_description, test_case_input, candidate_output, rubric_criteria)`.
- `RubricOutputs(quality, instruction_adherence, factual_structural, tone_format, reasoning)`
  com notas 1-5 validadas.
- `RubricError(judge_error, raw_response)` propagado se JSON inválido após retry —
  o judge NUNCA inventa nota.
- Prompt do judge tem:
  - System: instrução **anti-halo** explícita ("avaliar dimensões SEPARADAMENTE", "uma
    boa nota NÃO arrasta as outras").
  - User: tarefa, critérios, **3 âncoras many-shot** calibrando 1-5 (bom/médio/ruim),
    input, output, instruções de CoT campo a campo, schema JSON exato.
- `_extract_json` busca primeiro como JSON puro, depois extrai primeiro `{...}` do texto
  (tolera prosa em volta).
- `_validate` checa keys obrigatórias e range 1-5.
- Retry: 1 tentativa padrão + 1 retry com instrução de correção; depois `RubricError`.

### `app/evaluation/aggregate.py` — agregação pura

- `EvalResultRecord` (dataclass) desacopla do SQLAlchemy → testável sem DB.
- `ScorecardPayload` com 4 dimensões médias, aggregate_score, avg_latency_ms,
  total_cost_usd, failure_rate, variance, **per_slice_breakdown**.
- Pesos por `task_type`:
  - `structured_extraction`: factual_structural=0.40, instruction_adherence=0.30
  - `classification_response`: tone_format=0.30, instruction_adherence=0.30
- Score por record: `passed=False` ou `judge_error` → 0.0 (gate); senão weighted
  avg das 4 dimensões normalizadas (1-5 → 0-1).
- Variância: desvio padrão amostral médio das repetições do mesmo `test_case_id`.
- Breakdown por slice: cada slice tem aggregate_score, 4 dimensões, failure_rate, count.

### Testes (65 total, 50 novos neste bloco)

- `test_checks.py` (27 testes): cada check coberto com inputs OK/borda/inválido,
  incluindo o caso real `regex_negate_on_injection` detectando "reembolso de R$".
- `test_judge.py` (8 testes): retorno OK, parse de JSON em prosa, retry, error após
  retry, range 1-5, temperature=0.0, prompt contém "halo"/"independente" e "ÂNCORAS".
  Usa `ScriptedAdapter` (subclasse de `ModelAdapter` que retorna respostas pré-definidas).
- `test_aggregate.py` (10 testes): vazio, all-passed, drag de failures, slice
  breakdown, judge_error, variância entre reps, **caso âncora de regressão por slice**
  (typical=1.0, adversarial=0.0, global=0.8 → expõe regressão que a média esconde),
  pesos diferem por task_type, count por slice, cost/latency.

## Verificações executadas

| Comando | Resultado |
|---|---|
| `.venv/bin/ruff check app tests` | `All checks passed!` |
| `.venv/bin/mypy app` | `Success: no issues found in 35 source files` |
| `.venv/bin/pytest --cov=app/evaluation` | **65 passed in 4.51s**, **cobertura 93%** em `app/evaluation/` |

Quebra de cobertura por arquivo:
- aggregate.py: 96%
- judge.py: 95%
- json_schema_valid.py: 100%
- required_fields.py: 100%
- registry.py: 94%
- set_match.py / regex_match.py / exact_match.py / numeric_range.py: 81-89%

## Decisões/aprendizados deste bloco

- **`EvalResultRecord` desacoplado do SQLAlchemy.** O `aggregate` recebe um dataclass
  puro, não `EvalResult` ORM. Isso torna o teste trivial (sem fixtures de DB) e a função
  reutilizável (e.g., aggregate de um simulação sem persistir).
- **`judge_error` vai no campo `rubric_scores`** como `{"judge_error": "..."}` em vez
  de coluna separada. O aggregate detecta a chave e trata como score 0. Mantém o JSONB
  flexível e não exige migration nova.
- **Many-shot anchors hardcoded** no prompt. Calibração é tão importante que não vale
  parametrizar (cada task_type poderia ter anchors próprios — fica para iteração futura).
- **`temperature=0.0` no judge é o default** mas exposto para override em tests/debug.
- **`_extract_json` tolera prosa**. LLMs reais frequentemente adicionam "Claro, aqui está
  minha avaliação:" antes do JSON. A regex `\{[\s\S]*\}` pega o primeiro bloco.
- **Cobertura 93% > alvo de 80%.** As linhas não cobertas são caminhos defensivos
  (`config.field não informado`) que existem por contrato mas o seed não exercita.

## Próximo bloco

**Bloco 5 — Datasets + prompts versionados.**

Objetivos:
- `datasets/task_a_resume_matching.jsonl`: 30 casos JSONL.
  Distribuição: 18 typical / 6 edge / 3 known_failure / 3 adversarial.
  Cada linha: `{"id": ..., "slice": ..., "input": {resume_text, job_description},
  "expected": {match_score?, matched_skills?, missing_skills?}, "rubric_notes": "..."}`.
- `datasets/task_b_support.jsonl`: 30 casos análogos. Adversariais com prompt injection.
- `prompts/task_a/v1_baseline.yaml`..`v5_guardrails.yaml`: 5 YAMLs com
  `name, system_prompt, user_template, model_params, is_baseline`.
- `prompts/task_b/v1..v5.yaml`: idem.
- `scripts/validate_datasets.py`: valida JSONL parseável + distribuição de slices ±5%.
- Critério de aceite: `python -m scripts.validate_datasets` imprime "OK" para ambos.
