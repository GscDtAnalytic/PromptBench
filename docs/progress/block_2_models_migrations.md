# Bloco 2 — Backend skeleton + 7 models + migrations

## O que foi feito

- **`backend/Dockerfile`**: `python:3.12-slim` + `uv` para instalar deps.
- **`backend/pyproject.toml`** com:
  - build-system `hatchling`
  - deps: fastapi, uvicorn, pydantic, pydantic-settings, sqlalchemy[asyncio], asyncpg,
    psycopg[binary] (driver sync p/ alembic), alembic, arq, redis, httpx, anthropic,
    openai, tenacity, structlog, jsonschema, pyyaml, reportlab
  - deps[dev]: pytest, pytest-asyncio, pytest-cov, respx, ruff, mypy, types-pyyaml,
    types-jsonschema
  - ruff: target py312, regras `E,F,I,B,UP,N,SIM,RUF`, ignore RUF001/2/3 (PT-BR + ×)
  - mypy: `strict = true`
  - pytest: `asyncio_mode = "auto"`
- **`backend/app/core/`** — fundações:
  - `config.py`: `Settings` (pydantic-settings) carrega de `.env`, expõe
    `database_url`, `database_url_sync`, `redis_url`, `model_provider` (default `fake`),
    chaves opcionais, `cors_origins_list` property.
  - `db.py`: `Base` declarativa SQLAlchemy 2.0; `get_engine`, `get_session_factory`,
    `session_scope` (context manager com commit/rollback), `get_db` (dep FastAPI).
  - `logging.py`: `structlog` configurado com ConsoleRenderer.
  - `pricing.py`: `compute_cost_usd(input_tokens, output_tokens, p_in, p_out)` com
    `Decimal` para precisão; usada por todos os adapters.
- **`backend/app/models/`** — 7 entidades:
  - `enums.py`: `TaskType`, `SliceLabel`, `Provider`, `RunStatus` (todas `StrEnum`).
  - `task.py`: `Task` (1:N → PromptVersion, TestCase, EvalRun) com cascade delete.
  - `prompt_version.py`: `PromptVersion` com `UniqueConstraint(task_id, version_number)`
    e índice `ix_prompt_task_version`. Docstring grita "IMUTÁVEL".
  - `test_case.py`: `TestCase` com `__test__ = False` (evita warning do pytest).
    Índice `(task_id, slice)`.
  - `model_config.py`: `ModelConfig` com `UniqueConstraint(provider, model_name)`
    e colunas `price_per_1m_input`, `price_per_1m_output`.
  - `eval_run.py`: `EvalRun` com FKs CASCADE para task/prompt_version/model_config.
  - `eval_result.py`: `EvalResult` com `deterministic_scores` e `rubric_scores` em JSONB.
  - `scorecard.py`: `Scorecard` 1:1 com `EvalRun`; `per_slice_breakdown` JSONB.
- **`backend/app/main.py`**: FastAPI app com lifespan + CORS + `/health`.
- **Alembic** completo:
  - `alembic.ini`, `alembic/env.py` (usa `database_url_sync`), `alembic/script.py.mako`.
  - `alembic/versions/001_initial.py`: cria os 4 enums Postgres + 7 tabelas + índices
    + UniqueConstraints + FKs CASCADE. Hand-written (não autogenerate) para determinismo.
- **Testes** (`tests/test_models_import.py`, 7 testes):
  - tabelas registradas, mappers resolvem, unique constraint do prompt, 1:1 scorecard,
    cascades, imports.

## Verificações executadas

| Comando | Resultado |
|---|---|
| `uv venv .venv --python python3.12` | OK |
| `uv pip install -e ".[dev]"` | OK (~80 deps) |
| `.venv/bin/ruff check app tests` | `All checks passed!` |
| `.venv/bin/mypy app` | `Success: no issues found in 16 source files` |
| `.venv/bin/pytest -v` | `7 passed in 0.37s` |
| `.venv/bin/alembic upgrade head --sql` | gera SQL válido (CREATE TABLE × 7, índices, FKs CASCADE, INSERT alembic_version) |

## Decisões/aprendizados deste bloco

- **Enums em `StrEnum`** (Python 3.11+), não `class X(str, enum.Enum)` — ruff UP042 e
  StrEnum tem semântica mais limpa.
- **`__test__ = False` em `TestCase`** — sem isso, pytest interpreta o model como classe
  de teste e emite warning.
- **Migration hand-written.** Autogenerate exigiria um Postgres rodando — caminho mais
  longo do que escrever SQL determinístico direto.
- **Tipos `JSONB` em vez de `JSON`** — usamos Postgres, queremos os índices/operadores
  específicos de JSONB.
- **`compute_cost_usd` com `Decimal`** — `float * float / 1_000_000` introduz erros de
  ponto flutuante visíveis em LLMOps (cobramos por isso). 6 casas decimais.
- **mypy strict** revelou um type ignore desnecessário em `logging.py`; corrigido com
  annotation explícita.

## Próximo bloco

**Bloco 3 — Adapters (Fake/Claude/OpenAI/Gemini-stub) + smoke test.**

Objetivos:
- `app/adapters/base.py`: ABC `ModelAdapter` + dataclass `ModelResponse(text, input_tokens,
  output_tokens, latency_ms, raw)`. Método `async def call(system, user, params)`.
- `app/adapters/fake.py`: `FakeAdapter` determinístico. Tem um mapa
  `{(prompt_version_name, slice) -> output}` carregado de `app/adapters/fake_scripts.py`
  para que a regressão (v3 ganha em typical mas regride em adversarial) saia
  organicamente. Tokens/latência simulados realistas.
- `app/adapters/claude.py`, `openai.py`: implementações reais usando os SDKs. Testes
  unitários com `respx` mockando HTTP.
- `app/adapters/gemini.py`: stub que levanta `NotImplementedError`.
- `app/adapters/factory.py`: `get_adapter(provider)` retorna a impl certa.
- `scripts/smoke_adapter.py`: exercita FakeAdapter ponta-a-ponta + opção `--real`.
- Tests: `tests/test_adapters.py` cobrindo Fake (determinismo + custo) e Claude/OpenAI
  com mock HTTP.
- Critério de aceite: `pytest` verde com novos testes; smoke imprime
  `text, latency_ms, input_tokens, output_tokens, cost_usd` do FakeAdapter.
