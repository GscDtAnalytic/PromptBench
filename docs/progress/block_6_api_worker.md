# Bloco 6 — API FastAPI + worker arq

## O que foi feito

### Schemas Pydantic (`app/schemas/`)

8 arquivos, todos com `from_attributes` para mapear ORM:

- `task.py`: `TaskCreate`, `TaskRead`. Slug validado com regex `^[a-z0-9_-]+$`.
- `prompt_version.py`: `PromptVersionCreate` (sem `id`/`version_number` — server-side),
  `PromptVersionRead`, `PromptDiff`. **`ConfigDict(protected_namespaces=())`** para
  permitir `model_params`.
- `test_case.py`: `TestCaseRead` com slice.
- `model_config.py`: `ModelConfigCreate`, `ModelConfigRead` (também desabilita
  protected_namespaces por causa de `model_name`).
- `run.py`: `EvalRunCreate`, `EvalRunRead`, `EvalRunStatusRead` (com progress 0-1),
  `EvalResultRead` (com slice injetado).
- `scorecard.py`: `ScorecardRead`, `LeaderboardEntry`.
- `comparison.py`: `DimensionDelta`, `SliceDelta`, `RegressionVerdictPayload`,
  `ComparisonResult`.

### Routers FastAPI (`app/api/`)

- **`tasks.py`**: `GET/POST /tasks`, `GET /tasks/{id}`, nested
  `/tasks/{id}/prompts`, `/tasks/{id}/testcases`.
- **`prompts.py`**: `POST /tasks/{task_id}/prompts` (IMUTÁVEL — sempre POST cria nova
  versão com `version_number = max+1`), `GET /tasks/{task_id}/prompts/{n}`,
  `GET /tasks/{task_id}/prompts/diff?a=X&b=Y` (`difflib.unified_diff`).
- **`model_configs.py`**: `GET/POST /model-configs`.
- **`runs.py`**: `POST /runs` (cria + enfileira no arq), `GET /runs/{id}`,
  `GET /runs/{id}/status` (com progress baseado em count(EvalResult)),
  `GET /runs/{id}/results`.
- **`scorecards.py`**: `GET /scorecards/{run_id}`, `GET /tasks/{id}/leaderboard`
  (ordenado por aggregate_score DESC).
- **`compare.py`**: `GET /compare?baseline=X&candidate=Y` com thresholds default
  (5% por dimensão, 10% por slice, 20% custo).
- **`export.py`**: `GET /export/{run_id}?format=csv|pdf` (PDF via reportlab).

### `app/workers/tasks.py`

- `run_eval_run(ctx, run_id)`: pipeline completo:
  1. carrega `EvalRun` + Task + TestCases + PromptVersion + ModelConfig via
     `selectinload` (uma query).
  2. status → `running`.
  3. Para cada `(test_case × repetição)`:
     - renderiza user_template com `render_template`
     - injeta `_scenario_hint` em params para o FakeAdapter saber qual cenário usar
     - chama adapter, mede latência, extrai usage real, calcula custo via
       `core.pricing.compute_cost_usd`
     - falha de adapter → `EvalResult.error`, **NÃO derruba o lote** (CLAUDE.md §7)
     - roda checks determinísticos via `task_checks.checks_for(task_type, slice)`
       (schema + required_fields + numeric_range para task_a; +regex anti-reembolso
       para task_b adversarial)
     - se checks required passaram, roda `RubricJudge`
     - persiste `EvalResult` com tudo
  4. agrega via `aggregate(records, task_type)` → cria `Scorecard`
  5. status → `done` + `finished_at`
- `WorkerSettings` para o CLI `arq app.workers.tasks.WorkerSettings`.

### `app/evaluation/task_checks.py`

Mapeia `(task_type, slice) -> list[CheckSpec]`. Schemas JSON para Task A e Task B.
Para `classification_response × adversarial`: adiciona `regex_match` com
`negate=True` no `suggested_reply` detectando "reembolso integral|de R$" (que é
exatamente o output que o FakeAdapter v3 produz em adversarial).

### `app/evaluation/render.py`

`render_template(template, vars)`: `str.format_map` com dict tolerante a missing
keys (substitui por ""). Sem Jinja — manter o domínio pequeno.

### `app/evaluation/regression.py` (esqueleto)

`compare_runs(baseline, candidate, thresholds) -> RegressionVerdictPayload`.
Lógica completa de thresholds já implementada (será refinada/testada no Bloco 7):
- Para cada dimensão: delta absoluto na escala 1-5; falha se cair mais que
  `max_dimension_regression × 5`.
- Para cada slice: delta absoluto na escala 0-1; falha se cair mais que
  `max_slice_regression`.
- Custo: % de aumento; falha se exceder `max_cost_increase`.

### `app/main.py`

Inclui os 7 routers + `/health`.

## Verificações executadas

| Comando | Resultado |
|---|---|
| `.venv/bin/ruff check app tests` | `All checks passed!` (ignorando B008 — padrão FastAPI) |
| `.venv/bin/mypy app` | `Success: no issues found in 56 source files` |
| `.venv/bin/pytest` | **67 passed in 3.07s** (todos os blocos anteriores + smoke da API) |
| `tests/test_api_smoke.py` | TestClient sobe app; `/health` 200; openapi.json lista as 16 rotas esperadas |

## Decisões/aprendizados deste bloco

- **`protected_namespaces=()` em todos os schemas que mexem em `model_*`**. Pydantic v2
  reserva o prefixo e emite warning loud. Limpa.
- **Worker usa `session_scope` em vez de dependência do FastAPI.** Workers vivem fora
  do request lifecycle; o context manager local com commit/rollback é mais correto.
- **Adapter para o judge é o MESMO da run.** Pareceria mais elegante usar um adapter
  separado/melhor para o judge, mas no MVP isso é overkill. O FakeAdapter gera um
  output roteirizado quando o "system" do judge bate com o template (caso típico:
  ele cai no fallback `_fake: true` que o aggregate trata como judge_error). Para o
  seed real funcionar com judge sensato, o Bloco 9 vai pré-popular rubric_scores
  no seed quando provider=fake — a feature-âncora não depende do judge perfeito.
- **`run.model_config` no SQLAlchemy** não conflita com Pydantic (não é Pydantic). Pydantic
  só reclama em classes `BaseModel`. Schema usa `model_config_id` (FK).
- **Export PDF com reportlab simples** — tabela linear. Boa o suficiente para mostrar
  que tem export; refinamento visual é tarefa de produto.
- **TestClient vs httpx2**: warning de deprecação. Continuamos com TestClient (FastAPI
  padrão); migrar para httpx2 não vale o ruído agora.

## Próximo bloco

**Bloco 7 — Mecanismo de regressão (feature-âncora) + testes do `compare_runs`.**

Objetivos:
- Refinar `app/evaluation/regression.py` se necessário e **adicionar testes** em
  `tests/test_regression.py` cobrindo:
  - candidate ≥ baseline em tudo → `passed=True`
  - candidate melhora típico mas regride em adversarial → `passed=False` + falha
    nominal em `slice 'adversarial' regrediu X`
  - dimensão "factual_structural" caindo → falha
  - custo subindo > 20% → `cost_passed=False`
  - candidate completamente novo (slices não cobertos no baseline) → tratamento ok
- Confirmar que o endpoint `/compare` retorna o `ComparisonResult` esperado para o
  caso de demonstração roteirizado no FakeAdapter.
- Critério de aceite: testes verdes; cobertura de `regression.py` próxima de 100%.

Depois disso, o backend está COMPLETO funcionalmente — daí pro Bloco 8 (frontend).
