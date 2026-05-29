# PromptBench Studio

🌐 [English](README.md) · **Português**

Aplicações LLM regridem em produção quando prompts mudam sem controle, e a queda de
qualidade só aparece depois que o usuário reclama. O PromptBench Studio trata prompts
como ativos de software (versionados, medidos e comparados com método) e torna as
regressões detectáveis antes do deploy.

## O que este projeto prova

- Versiona prompts como ativos imutáveis e auditáveis, com histórico de quem mudou o quê e qual foi o impacto.
- Constrói datasets com slices de avaliação (typical, edge, known_failure, adversarial) que expõem riscos reais.
- Mede custo, latência, variância e qualidade com rigor: tokens vindos do provedor, desvio padrão entre repetições e um judge calibrado.
- Detecta regressões antes da produção com veredito por dimensão e por slice, não apenas pela média global.

## Demo em vídeo

<video src="docs/demo.mp4" controls muted width="100%"></video>

[▶️ Assistir ao demo](https://github.com/user-attachments/assets/demo.mp4)

O vídeo mostra o fluxo completo: navegar pelas tasks, abrir a rubrica, rodar um
experimento, ler o scorecard por slice e comparar duas versões até o veredito de
regressão. Aparecem tanto runs `fake` (determinísticos, sem chave de API) quanto runs
reais em `claude-haiku-4-5`, lado a lado com latência e custo reais. Se o player acima
não carregar, use o link direto: [`docs/demo.mp4`](docs/demo.mp4) (ou
[`docs/demo.mov`](docs/demo.mov)).

---

> **Como funciona.** Roda múltiplas versões de prompt em múltiplos modelos, mede
> qualidade, latência e custo, e detecta regressões que a média global esconde,
> olhando slice a slice (typical, edge, known_failure, adversarial).
>
> `PromptVersion` é imutável, variância é métrica de primeira classe, custo vem do
> `usage` real do provedor, e o veredito de regressão aprova ou reprova uma versão
> avaliando cada slice individualmente.

---

## 1. Arquitetura em uma página

```
                ┌────────────────────────┐
                │   Frontend (Next.js)   │
                │   App Router + TSX     │
                │   Recharts • Tailwind  │
                └───────────┬────────────┘
                            │  fetch (REST tipado)
                            ▼
                ┌────────────────────────┐         ┌──────────────────┐
                │   Backend (FastAPI)    │ ──────▶ │  Postgres 16     │
                │   Pydantic v2          │         │  (7 entidades)   │
                │   SQLAlchemy 2.0       │         └──────────────────┘
                └───────────┬────────────┘
                            │  enqueue
                            ▼
                ┌────────────────────────┐         ┌──────────────────┐
                │   Worker (arq)         │ ──────▶ │  Redis           │
                │   run_eval_run(run_id) │         └──────────────────┘
                └───────────┬────────────┘
                            │ chama
                            ▼
        ┌───────────────────────────────────────────┐
        │     ModelAdapter (ABC)                    │
        │   ┌──────────┬──────────┬──────────┐      │
        │   │  Fake    │  Claude  │  OpenAI  │ ...  │
        │   └──────────┴──────────┴──────────┘      │
        └───────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────────┐
        │     evaluation/                           │
        │   ┌──────────┬─────────────┬──────────┐   │
        │   │ checks/  │ RubricJudge │ aggregate│   │
        │   │ (puro)   │ (LLM-judge) │ + variâ. │   │
        │   └──────────┴─────────────┴──────────┘   │
        │   ┌──────────────────────────────────┐    │
        │   │  regression.compare_runs         │    │
        │   │  (veredito por dim+slice+custo)  │    │
        │   └──────────────────────────────────┘    │
        └───────────────────────────────────────────┘
```

### As 7 entidades

`Task` · `PromptVersion` (imutável) · `TestCase` (com `slice`) · `ModelConfig`
(com pricing) · `EvalRun` (status + repetitions) · `EvalResult` (raw_output,
latency, tokens, cost, deterministic_scores, rubric_scores) · `Scorecard`
(4 dimensões + custo + latência + variância + `per_slice_breakdown`).

### As 4 decisões arquiteturais (resumo dos ADRs)

| # | Decisão | Razão curta |
|---|---|---|
| ADR-1 | **arq** (async-native, Redis) como worker | FastAPI é async-first; Celery é overkill no MVP; BackgroundTasks morre com o processo. |
| ADR-2 | **PromptVersion = snapshot imutável** | O produto vende imutabilidade auditável; armazenar a string é barato; o diff é trivial na leitura. |
| ADR-3 | **`ModelAdapter` ABC + implementações por provedor** | Cada provedor expõe `usage` diferente; queremos medir latência localmente e custo pela pricing-table; o litellm mascara esses dados. |
| ADR-4 | **Módulo de avaliação puro + judge isolado** | Testabilidade do coração do sistema; checks como funções puras; adicionar um check novo é 1 arquivo, sem mexer no core. |

Detalhes completos em [`docs/ADR.md`](docs/ADR.md).

---

## 2. Telas

### Tasks (home)

Cada task expõe suas versões de prompt, o dataset por slice e os runs recentes. A
atividade recente já mostra runs reais em `claude-haiku-4-5` ao lado dos runs `fake`.

![Tasks](docs/screenshots/tasks-home.png)

### Detalhe da task

Dataset com distribuição de slices (60/20/10/10), rubrica com 4 dimensões avaliadas de
forma independente, e as versões de prompt v1 → v5 numa progressão deliberada.

![Detalhe da task](docs/screenshots/task-detail.png)

### Contrato da rubrica e âncoras de calibração

O contrato completo do judge: descrição da task, critérios por dimensão e âncoras
many-shot (bom, médio, ruim) que calibram a escala 1–5.

![Âncoras da rubrica](docs/screenshots/rubric-anchors.png)

### Rodar experimento e leaderboard

Dispara N repetições do dataset para estimar variância. O leaderboard ranqueia os runs
concluídos por score, com latência, custo real e taxa de falha lado a lado; empate
técnico resolve pelo mais barato.

![Leaderboard](docs/screenshots/leaderboard.png)

### Scorecard do run

KPIs do run (aggregate score, latência média, custo total, taxa de falha), radar das 4
dimensões da rubrica com a variância (σ) entre repetições, e o score por slice. O
veredito de regressão olha para as barras por slice, não para a média.

![Scorecard do run](docs/screenshots/run-scorecard.png)

### Amostras do judge

Transparência do LLM-as-judge: para cada amostra, as notas por dimensão e o raciocínio
campo a campo que justifica cada nota com evidência do output.

![Amostras do judge](docs/screenshots/judge-samples.png)

### Comparar runs

Veredito por dimensão, slice e custo. O score global pode subir enquanto um slice
regride ou enquanto o custo estoura o orçamento, e esta tela existe para expor isso.
Duas comparações reais em `claude-haiku-4-5`:

**Reprovado.** O candidate v4 tem score maior na média (0.936 vs 0.896) e melhora a
maioria dos slices, mas o veredito reprova porque o custo subiu 89.3% contra o limite de
+20%. Ser melhor na média não garante promoção quando estoura o orçamento de custo.

![Comparar runs, veredito reprovado](docs/screenshots/compare-rejected.png)

**Aprovado.** O mesmo candidate v4 (0.936) contra o baseline ingênuo v1 (0.000): toda
dimensão e todo slice melhoram, e o custo ainda cai 3.3%. Seguro para promover.

![Comparar runs, veredito aprovado](docs/screenshots/compare-approved.png)

O veredito é a conjunção `dimensão ∧ slice ∧ custo`: reprovar em qualquer um bloqueia a
promoção.

---

## 3. Como rodar

### Requisitos
- Docker + Docker Compose.
- Chaves Anthropic/OpenAI são opcionais. O MVP roda sem elas: o `FakeAdapter`
  determinístico produz outputs roteirizados realistas, incluindo o caso de regressão
  adversarial. Para usar provedores reais, copie `.env.example` para `.env` e preencha
  as chaves. O Claude já está integrado e roda ao vivo.

### Subir tudo

```bash
docker compose up --build       # postgres + redis + backend + worker + frontend
```

Depois que os serviços subirem (alguns segundos), aplique a migration e popule os dados
de demonstração:

```bash
make migrate.up
make seed
```

O `make seed` cria 2 Tasks, 60 TestCases (30 por task na distribuição 60/20/10/10),
10 PromptVersions (5 por task, v1 baseline até v5 guardrails), 2 ModelConfigs
`fake-fast` e `fake-thorough`, e roda 4 EvalRuns de demonstração (v1 e v3 para cada
task) produzindo Scorecards e o caso de regressão âncora.

Acesse:
- **Frontend**: http://localhost:3000
- **Backend (OpenAPI)**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

### Outros comandos úteis (Makefile)

```bash
make help                # lista todos os alvos
make test                # pytest no backend
make test.scoring        # apenas testes da camada de avaliação, com cobertura
make lint                # ruff
make typecheck           # mypy strict
make check               # lint + typecheck + test, backend e frontend
make validate-datasets   # confere o JSONL e a distribuição de slices
make migrate.new name="descricao"   # cria nova migration
```

### Rodar fora do docker

```bash
# Backend
cd backend
uv venv .venv --python python3.12
uv pip install --python .venv/bin/python -e ".[dev]"
DATABASE_URL_SYNC="postgresql+psycopg://promptbench:promptbench@localhost:5432/promptbench" \
DATABASE_URL="postgresql+asyncpg://promptbench:promptbench@localhost:5432/promptbench" \
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

---

## 4. O que torna este projeto diferente de um CRUD

### a) Prompts são ativos versionados, sem exceção

Não existe `UPDATE` em `prompt_versions`. Editar significa um `POST` que cria uma nova
versão com `version_number = max+1` em transação atômica. Todo `EvalResult` aponta para
o `prompt_version_id` exato que o gerou, o que garante reprodutibilidade total.

### b) Variância é métrica de primeira classe

Cada EvalRun roda `repetitions >= 3` por test_case. O Scorecard expõe o desvio padrão
médio entre repetições. Output não-determinístico exige isso: reportar média sem desvio
é uma verdade pela metade.

### c) Score global nunca esconde regressão de slice

Toda comparação quebra por `typical`, `edge`, `known_failure` e `adversarial`. O
mecanismo de regressão (`evaluation/regression.py`) aplica thresholds por slice, não só
na média. Exemplo real produzido pelo `make seed`:

```
task_a_resume_matching:
  v1 aggregate=0.467  v3=0.750     # v3 melhorou na média
  veredito: REPROVADO              # mas falha no detalhe:
    - dimensão 'factual_structural' caiu -0.30 (limite -0.25)
    - slice 'adversarial' regrediu -0.167 (limite -0.100)
    - custo subiu 179.3% (limite +20.0%)
```

A média subiu e o veredito reprovou. Esse é o ponto do produto.

### d) Custo e tokens vêm da resposta real do provedor

Nenhum adapter estima tokens. O SDK da Anthropic/OpenAI reporta `usage`, e o custo é
`usage × ModelConfig.price_per_1m_*` calculado em `core/pricing.compute_cost_usd` com
`Decimal` (6 casas decimais, porque LLMOps cobra por isso).

### e) O judge não inventa nota

O `RubricJudge` valida JSON estrito (4 dimensões de 1 a 5 + reasoning), faz 1 retry em
erro de parse, e na falha persistente propaga `judge_error` sem preencher default. O
prompt do judge usa CoT campo a campo, âncoras many-shot (bom, médio, ruim) e instrução
anti-halo explícita.

### f) Checks determinísticos são funções puras

`evaluation/checks/` tem 6 checks registráveis (`json_schema_valid`,
`required_fields_present`, `exact_match`, `set_match`, `regex_match`, `numeric_range`),
cada um com a mesma assinatura `(output, expected, config) -> CheckResult`. Adicionar um
check novo é 1 arquivo + 1 linha no registry. A cobertura de testes do módulo
`evaluation/` é de 87%.

---

## 5. As 2 tarefas

### Task A — Resume × Job Matching (`structured_extraction`)
- Input: `{resume_text, job_description}`
- Output esperado: JSON `{match_score, matched_skills, missing_skills, ranking_justification}`
- Risco-alvo: alucinar skills que não estão no texto-fonte; prompt injection no
  `resume_text` inflando o `match_score`.

### Task B — Atendimento (`classification_response`)
- Input: `{customer_message, account_context}`
- Output esperado: JSON `{category, priority, suggested_reply, requires_human}`
- Risco-alvo: categoria fora do enum; promessa de reembolso indevida (injection do
  cliente); vazamento de dado de outras contas.

Cada task tem 30 casos no JSONL, na distribuição 60% typical, 20% edge, 10%
known_failure e 10% adversarial. São 5 versões de prompt em YAML, numa progressão
deliberada: v1 baseline ingênuo, v2 JSON, v3 few-shot, v4 CoT, v5 guardrails.

---

## 6. O que eu mediria diferente em produção

O MVP entrega o ciclo experimentar → medir → comparar → vetar. Em produção, eu
adicionaria:

1. **Calibração do judge contra human labels.** Anotar 50 a 100 casos manualmente e
   medir a correlação (Spearman/Kendall) entre o judge e a anotação humana, por
   dimensão. Sem calibração, o judge é uma régua sem ponto zero: pode estar
   sistematicamente lenient ou strict.

2. **Judge multi-modelo com voto majoritário (ou júri).** Hoje é 1 LLM. Em produção,
   rodar o mesmo prompt em 3 modelos diferentes (Claude, OpenAI, Gemini) e usar
   mediana ou majority-vote reduz o viés de um único provedor.

3. **Eval contínua em produção (drift).** Re-rodar o eval com tráfego real amostrado e
   comparar com o scorecard de homologação. Alertar quando o slice de tráfego real
   diverge mais que X% do synthetic-typical.

4. **Tracking de pricing histórico.** O `ModelConfig.price` atual é um snapshot. Em
   produção, pricing tem histórico versionado. Re-rodar um experimento antigo com o
   preço novo deveria continuar reprodutível.

5. **Auto-classificação de slices em novos test cases.** Os slices hoje são anotados
   manualmente. Em produção, um classificador (regex + LLM com confidence) marcaria os
   casos novos chegando do tráfego para alimentar o slice known_failure.

6. **Métrica de injection success rate explícita.** Hoje a injection bem-sucedida sai
   de forma indireta (`match_score=100` + `missing=[]` no slice adversarial). Em
   produção, isso vira um check explícito com taxa reportada no Scorecard.

7. **Caching de outputs com fingerprint de (prompt_version × test_case × model).**
   Re-rodar para gerar gráficos novos não deveria re-pagar tokens, apenas re-agregar.

8. **PR check no GitHub Actions.** `compare_runs(baseline, candidate)` rodando
   automaticamente em PRs que tocam `prompts/`, falhando o build quando o veredito for
   REPROVADO. O mecanismo já existe; falta apenas o glue no CI.

---

## 7. Trilha de auditoria do build

Cada bloco da construção tem um arquivo em `docs/progress/block_N_*.md` com o que foi
feito, as verificações executadas (lint, typecheck, test), as decisões não-óbvias e o
objetivo do bloco seguinte. É a explicação reversa de como o sistema foi construído.
</content>
