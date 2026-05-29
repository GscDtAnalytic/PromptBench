# Bloco 1 — ADRs + scaffold + docker-compose

## O que foi feito

- Estrutura de pastas do monorepo criada:
  - `backend/{app/{core,models,schemas,api,adapters,evaluation/checks,workers},tests,alembic/versions}`
  - `frontend/`
  - `datasets/`, `prompts/{task_a,task_b}/`
  - `docs/progress/`, `scripts/`
- **`docs/ADR.md`** com os 4 ADRs no formato `Contexto / Alternativas / Decisão / Consequências`:
  - ADR-1: `arq` como worker async-native (vs Celery/BackgroundTasks)
  - ADR-2: PromptVersion snapshot completo imutável (vs event-sourcing)
  - ADR-3: Adapter ABC + impls específicas (vs litellm/dict de funções)
  - ADR-4: Módulo de avaliação puro + judge isolado (vs YAML/worker-monolítico)
- **`docker-compose.yml`** com 5 serviços: `postgres:16-alpine`, `redis:7-alpine`,
  `backend` (uvicorn), `worker` (arq), `frontend` (next dev). Healthchecks em postgres
  e redis; volumes para hot-reload do backend e frontend; volumes read-only para
  `/datasets` e `/prompts` (montados de fora pra dentro).
- **`.env.example`** com `DATABASE_URL` (async e sync), `REDIS_URL`, `MODEL_PROVIDER=fake`
  default, slots para chaves reais (vazios), CORS_ORIGINS, NEXT_PUBLIC_API_BASE_URL.
- **`Makefile`** com 24 alvos: compose (up/down/logs/ps/build), seed, validate-datasets,
  backend (dev/test/test.scoring/lint/fmt/typecheck), migrations (new/up/down/history),
  frontend (dev/lint/build/shell), `check` global. Carrega `.env` se presente.
- **`.gitignore`** cobrindo Python, Node/Next, IDEs, build, logs.

## Verificações executadas

| Comando | Resultado |
|---|---|
| `docker compose config -q` | OK (sem erros de YAML) |
| `make help` | Listou os 24 alvos corretamente |
| Estrutura de diretórios | `ls -la` mostra 7 pastas + arquivos esperados |

## Decisões/aprendizados deste bloco

- O `.env` é carregado pelo Makefile com `include` condicional (`ifneq (,$(wildcard ./.env))`)
  pra não falhar quando ele ainda não existir (e.g., em CI).
- `MODEL_PROVIDER=fake` é o default em todo lugar (Makefile, docker-compose, .env.example).
  Isso garante que a app sempre roda sem chaves reais — o caminho fake é cidadão de 1ª classe.
- Os Dockerfiles de `backend` e `frontend` ficam para o Bloco 2 e Bloco 8 respectivamente
  (eles dependem do `pyproject.toml` e do `package.json` que ainda não existem).
- O service `worker` aponta para `arq app.workers.tasks.WorkerSettings` — esse módulo
  será criado no Bloco 6.

## Próximo bloco

**Bloco 2 — Backend skeleton + 7 models + migrations.**

Objetivos:
- Criar `backend/Dockerfile` (Python 3.12-slim + uv) e `backend/pyproject.toml` com deps:
  fastapi, sqlalchemy[asyncio], asyncpg, psycopg[binary] (sync, p/ alembic), alembic,
  pydantic, pydantic-settings, arq, httpx, anthropic, openai, structlog, jsonschema,
  tenacity, pytest, pytest-asyncio, pytest-cov, ruff, mypy.
- Implementar 7 modelos em `backend/app/models/`: `Task`, `PromptVersion`, `TestCase`,
  `ModelConfig`, `EvalRun`, `EvalResult`, `Scorecard`. SQLAlchemy 2.0 declarative com
  `Mapped`/`mapped_column`. Enums: `TaskType`, `SliceLabel`, `Provider`, `RunStatus`.
- Implementar `app/core/config.py` (pydantic-settings), `app/core/db.py` (engine async +
  session factory), `app/core/logging.py` (structlog).
- Alembic init + migration `001_initial.py` com as 7 tabelas e índices em
  `(task_id, version_number)`, `(eval_run_id)`, `(task_id)` em scorecards.
- Critério de aceite: `make migrate.up` aplica limpo (vou rodar pelo container);
  `make lint` e `make typecheck` verdes.
