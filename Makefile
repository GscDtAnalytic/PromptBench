.DEFAULT_GOAL := help
SHELL := /bin/bash

# Carrega .env se existir (não falha se não houver)
ifneq (,$(wildcard ./.env))
	include .env
	export
endif

BACKEND_DIR := backend
FRONTEND_DIR := frontend

# ---------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------
.PHONY: help
help: ## Lista os alvos disponíveis
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_.-]+:.*?## / {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ---------------------------------------------------------------------
# Compose / orquestração
# ---------------------------------------------------------------------
.PHONY: up down logs ps build
up: ## Sobe a stack (docker-compose up --build)
	docker compose up --build

down: ## Derruba a stack
	docker compose down

logs: ## Logs da stack
	docker compose logs -f --tail=200

ps: ## Status dos containers
	docker compose ps

build: ## Rebuilda imagens
	docker compose build

# ---------------------------------------------------------------------
# Seed / datasets
# ---------------------------------------------------------------------
.PHONY: seed validate-datasets
seed: ## Popula DB com 2 tasks, datasets, prompts, modelos e 2 EvalRuns de demo
	docker compose exec backend python -m scripts.seed

validate-datasets: ## Valida os JSONL dos datasets
	docker compose exec backend python -m scripts.validate_datasets

# ---------------------------------------------------------------------
# Provedores reais (opt-in — exigem chave no .env, gastam tokens)
# ---------------------------------------------------------------------
.PHONY: smoke run.real
smoke: ## Smoke test dos adapters reais (1 chamada barata por provider com chave)
	docker compose exec backend python -m scripts.smoke_providers

run.real: ## EvalRun real end-to-end com cost cap (vars: PROVIDER MODEL TASK PV REPS MAX_CASES)
	docker compose exec backend python -m scripts.run_real \
		--provider $(or $(PROVIDER),claude) \
		--model $(or $(MODEL),claude-haiku-4-5) \
		--task $(or $(TASK),task_a_resume_matching) \
		--prompt-version $(or $(PV),4) \
		--reps $(or $(REPS),3) \
		--max-cases $(or $(MAX_CASES),3)

# ---------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------
.PHONY: backend.dev backend.shell test test.scoring lint fmt typecheck
backend.dev: ## Backend em modo dev (reload) — usar dentro do container ou com venv local
	cd $(BACKEND_DIR) && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

backend.shell: ## Shell no container do backend
	docker compose exec backend bash

test: ## Roda pytest (backend)
	docker compose exec backend pytest -v

test.scoring: ## Roda só os testes da camada de avaliação (com cobertura)
	docker compose exec backend pytest -v tests/test_checks.py tests/test_aggregate.py tests/test_regression.py tests/test_judge.py --cov=app/evaluation --cov-report=term-missing

lint: ## ruff check
	docker compose exec backend ruff check app tests

fmt: ## ruff format
	docker compose exec backend ruff format app tests

typecheck: ## mypy
	docker compose exec backend mypy app

# ---------------------------------------------------------------------
# Migrations
# ---------------------------------------------------------------------
.PHONY: migrate.new migrate.up migrate.down migrate.history
migrate.new: ## Cria nova migration: make migrate.new name="descricao"
	docker compose exec backend alembic revision --autogenerate -m "$(name)"

migrate.up: ## Aplica migrations
	docker compose exec backend alembic upgrade head

migrate.down: ## Reverte 1 migration
	docker compose exec backend alembic downgrade -1

migrate.history: ## Mostra histórico de migrations
	docker compose exec backend alembic history

# ---------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------
.PHONY: frontend.dev frontend.lint frontend.build frontend.shell
frontend.dev: ## Frontend dev (Next.js)
	cd $(FRONTEND_DIR) && npm run dev

frontend.lint: ## eslint + tsc --noEmit
	docker compose exec frontend npm run lint && docker compose exec frontend npx tsc --noEmit

frontend.build: ## Build de produção do frontend
	docker compose exec frontend npm run build

frontend.shell: ## Shell no container do frontend
	docker compose exec frontend sh

# ---------------------------------------------------------------------
# Verificação completa
# ---------------------------------------------------------------------
.PHONY: check
check: lint typecheck test frontend.lint ## lint + typecheck + test (back + front)
	@echo "=== check verde ==="
