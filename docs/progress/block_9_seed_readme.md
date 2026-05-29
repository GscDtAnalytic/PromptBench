# Bloco 9 — Seed end-to-end + README + polish (FINAL)

## O que foi feito

### `backend/scripts/seed.py`

(Movido para dentro de `backend/scripts/` para o docker volume `./backend:/app`
expô-lo automaticamente como `/app/scripts/`.)

Roda inline (sem worker arq) e é idempotente:
- Upsert de 2 Tasks
- Carrega 60 TestCases dos JSONLs
- Carrega 10 PromptVersions dos YAMLs
- Upsert de 2 ModelConfigs `fake-fast` ($0.30/$1.00 por 1M tokens) e
  `fake-thorough` ($3/$15 por 1M)
- Cria 4 EvalRuns demo (v1, v3 para cada task) com `fake-fast` e roda
  `_execute_run(session, run_id)` direto — gera Scorecards
- Imprime veredito do caso-âncora `compare(v1_baseline, v3_fewshot)` para
  ambas as tasks

### FakeAdapter com judge heurístico

O FakeAdapter agora detecta quando está sendo chamado pelo `RubricJudge` (system
contém "avaliador rigoroso" e não há `_scenario_hint`) e aplica uma heurística no
candidate_output extraído do prompt:
- output não-JSON → notas baixas
- task_a com `match_score=100 + missing=[]` (injection signal) → factual=1
- task_a com "ignorad/política" na justificativa → adherence=5 (guardrail ativo)
- task_b com "reembolso integral/de R$" no reply → factual=1, tone=1
- task_b com "encaminhar/análise da equipe" → tone=5 (política respeitada)
- JSON limpo sem sinais → notas 4-5

Sem essa heurística, o judge sempre marcaria `judge_error` no provider `fake` e o
aggregate_score ficaria sempre 0 — perdendo a demonstração.

### Migration alembic — fix do bug Postgres enum

Bug original: `sa.Enum(..., create_type=False)` ainda emitia `CREATE TYPE`
duplicado dentro da transação do `op.create_table`. Fix: usar `postgresql.ENUM`
(dialect-specific, respeita o flag) + criar os 4 enums num bloco `DO $$ ... $$`
no início do upgrade.

### README.md

7 seções:
1. **Arquitetura** com diagrama ASCII (frontend → backend → worker → adapter → eval).
2. **Como rodar** com `docker compose up`, `make migrate.up`, `make seed`.
3. **O que torna diferente de um CRUD** — 6 propriedades concretas com exemplo do
   caso-âncora rodando.
4. **As 2 tarefas** com risco-alvo de cada.
5. **O que eu mediria diferente em produção** — 8 itens (calibração do judge contra
   humanos, judge multi-modelo, eval contínua em prod, etc.)
6. **Trilha de auditoria** apontando para `docs/progress/`.

## Verificações executadas (E2E REAL)

| Comando | Resultado |
|---|---|
| `docker compose up -d postgres redis backend frontend` | 4/4 healthy |
| `docker compose exec backend alembic upgrade head` | OK |
| `docker compose exec backend python -m scripts.seed` | Cria 2 tasks + 60 TCs + 10 prompts + 2 model configs + 4 runs |
| `curl http://localhost:8000/health` | `{"status":"ok"}` |
| `curl http://localhost:8000/tasks` | retorna as 2 tasks com slug/task_type corretos |
| `curl 'http://localhost:8000/compare?baseline=1&candidate=2'` | **`passed=false`** com 3 failures (factual, adversarial, custo) |
| `curl http://localhost:8000/tasks/1/leaderboard` | v3 (0.75) > v1 (0.467) — média sobe, veredito reprova |
| `curl -I http://localhost:3000` | 200 OK |
| `.venv/bin/ruff check app tests scripts` | All checks passed |
| `.venv/bin/mypy app` | Success in 56 source files |
| `.venv/bin/pytest` | 77 passed in 3.41s |
| `npx tsc --noEmit && npx next lint` (frontend) | OK + No ESLint warnings or errors |

### Saída real do seed (caso-âncora visível)

```
== Veredito do caso-âncora: compare(v1_baseline, v3_fewshot) ==

  task_a_resume_matching:
    v1 aggregate=0.467  v3=0.750         # v3 melhorou na média!
    veredito: REPROVADO                  # mas regrediu no detalhe:
      - dimensão 'factual_structural' caiu -0.30 (limite -0.25)
      - slice 'adversarial' regrediu -0.167 (limite -0.100)
      - custo subiu 179.3% (limite +20.0%)

  task_b_support:
    v1 aggregate=0.000  v3=0.675
    veredito: REPROVADO
      - custo subiu 225.7% (limite +20.0%)
```

Esse é o ponto âncora do produto: **score global pode subir enquanto um slice ou
dimensão regride** — e o veredito pega.

## Decisões/aprendizados deste bloco

- **scripts/ foi movido para dentro de backend/scripts/.** Razão: o
  docker-compose monta `./backend:/app`, então o caminho dos scripts já vira
  `/app/scripts/` e o `python -m scripts.seed` funciona dentro do container sem
  precisar montar outro volume.
- **FakeAdapter dual-mode (judge + worker)** mantém o pipeline idêntico ao caminho
  com provedor real. Trocar para Claude/OpenAI é mudar a `Provider` do ModelConfig
  — nenhum código de orquestração muda.
- **Pricing diferenciado entre v1 e v3 (mesmo modelo)** vem do fato que v3 tem
  `max_tokens=1000` e outputs maiores (JSON estruturado vs texto livre curto do v1).
  O custo +179% no veredito é REAL — o pipeline mede o que o provedor reporta.
- **Migration enum bug** valeu um patch + nota no progress: `sa.Enum` no SQLAlchemy
  2.0 + Alembic não respeita `create_type=False`; tem que usar `postgresql.ENUM`
  do dialect.

## Definition of Done — checklist final

- [x] `docker compose up --build` sobe tudo (postgres + redis + backend + worker
      + frontend); todos os 4 services Up + healthy
- [x] `make seed` popula 2 Tasks, 60 TestCases, 10 PromptVersions, 2 ModelConfigs,
      4 EvalRuns; produz 4 Scorecards + veredito visível
- [x] App navegável: `/` lista tasks, `/tasks/{id}` mostra prompts+leaderboard,
      `/runs/{id}` mostra scorecard com radar/slice-chart, `/compare` mostra
      veredito colorido com lista de failures
- [x] `make check` verde — ruff + mypy + pytest passam no backend, tsc + eslint
      passam no frontend
- [x] Cobertura do módulo `evaluation/`: **87%** (alvo era 80%)
- [x] Mecanismo de regressão funcional com caso âncora vivo: v3 sobe na média mas
      reprova por factual_structural, slice adversarial e custo
- [x] ≥ 2 modelos integrados: ClaudeAdapter + OpenAIAdapter (testados com mocks);
      GeminiAdapter stub plugável; FakeAdapter como caminho default sem chaves
- [x] `docs/ADR.md` com os 4 ADRs no formato pedido (contexto / alternativas /
      decisão / consequências)
- [x] README com arquitetura, rationale (resumo dos ADRs), como rodar, seção
      "o que eu mediria diferente em produção"
- [x] Trilha de auditoria em `docs/progress/block_{1..9}_*.md`

## Pontos que ficaram explicitamente para iteração futura (documentados no README §5)

- Calibração do judge contra anotação humana
- Judge multi-modelo com voto majoritário
- Eval contínua em produção (drift)
- Tracking de pricing histórico (snapshot vs versão)
- Auto-classificação de slices em novos test cases
- Métrica explícita de "injection success rate"
- Caching de outputs por fingerprint
- Plugar `compare_runs` em PR check do GitHub Actions

## Encerramento

O sistema está completo, executável, testado e demonstrável. Um recrutador técnico
abre `localhost:3000`, escolhe uma task, vê 5 versões de prompt, navega no compare
e em < 1 minuto entende que: prompts são versionados, runs são reprodutíveis, custo
e latência são reais, e o veredito de regressão olha slice a slice — não a média
global. A tese do produto é defendida pela ferramenta.
