# Architecture Decision Records — PromptBench Studio

Este documento registra as decisões arquiteturais não-óbvias do projeto. Toda decisão
que modifique uma das escolhas abaixo precisa de um novo ADR neste arquivo.

---

## ADR-1: Execução assíncrona de avaliações em lote — `arq`

**Status:** Aceito · 2026-05-28

**Contexto.** O worker precisa consumir EvalRuns (cada run = `N test_cases × R repetições`
chamadas a um modelo + scoring), persistir resultados parciais, tolerar falha de provedor
sem derrubar o lote, e expor progresso para polling pelo frontend. O MVP roda em
docker-compose local, mas a arquitetura precisa ser "pronta para crescer".

**Alternativas consideradas.**

- **A — Celery + Redis broker.** Maduro, ecossistema vasto, monitoramento (Flower) pronto.
  Custos: setup pesado (broker, worker, beat), API síncrona herdada de Python pré-async;
  driver assíncrono ainda é segunda-classe. Overkill para o MVP.
- **B — FastAPI `BackgroundTasks`.** Zero setup, vive no mesmo processo. Custos: morre
  com o processo, sem retry policy, sem fila durável, sem dashboards. Quebra na primeira
  reinicialização — incompatível com "pronto para crescer".
- **C — `arq` (escolhido).** Worker async-native sobre Redis, tarefas são `async def`,
  ergonomia FastAPI-style. Custos: ecossistema menor que Celery; menos plugins prontos.

**Decisão.** Adotar **`arq`** no MVP. O worker mora num container separado (`worker` no
docker-compose) consumindo do mesmo Redis. Cada `EvalRun` vira um job; o job persiste
`EvalResult`s à medida que avança (para o frontend poder mostrar progresso real, não
um spinner cego).

**Consequências.**
- **Ganhamos:** async-native compatível com adapters HTTP async, baixa complexidade, fila
  durável persistindo em Redis, retry/backoff configurável por job.
- **Sacrificamos:** monitoramento out-of-the-box (sem Flower/Sentry-Celery integração);
  ecossistema menor.
- **A revisitar ao escalar.** Se aparecer necessidade de fluxos longos com checkpoints,
  cron complexo, ou observabilidade rica, considerar Celery ou Temporal. A interface do
  worker é uma única função `run_eval_run(ctx, run_id)` — trocar de runner é localizado.

---

## ADR-2: Versionamento de prompts — snapshot completo imutável

**Status:** Aceito · 2026-05-28

**Contexto.** A tese central do produto é **"prompts são ativos versionados"**. O sistema
precisa permitir auditoria (qual texto exato gerou cada `EvalResult`), reprodutibilidade
(re-rodar um experimento histórico) e comparação visual entre versões. Storage de strings
é barato; ambiguidade não é.

**Alternativas consideradas.**

- **A — Tabela `prompt_versions` com `version_number` incremental + diff calculado on-read.**
  Cada `PromptVersion` armazena o conteúdo completo, é imutável após criada. Histórico
  trivial; diff entre versões é computado quando solicitado.
- **B — Snapshot completo com normalização interna.** Variante de A onde campos são
  decompostos (system, user_template, model_params). Adotado em conjunto com A.
- **C — Event-sourcing por delta.** Cada alteração vira um evento; a versão atual é
  reconstruída aplicando deltas. Custos: complexidade alta, debug difícil, sem ganho
  prático no domínio (prompts têm dezenas a centenas de linhas, não terabytes).

**Decisão.** **Snapshot completo imutável por versão.** A tabela `prompt_versions` tem
`UPDATE` proibido por convenção (validado no router: `POST` é o único caminho que cria
linha; não há endpoint `PUT/PATCH`). "Editar um prompt" = `POST` que cria nova linha com
`version_number = max(existing) + 1` em transação atômica.

**Consequências.**
- **Ganhamos:** auditabilidade total — todo `EvalResult` aponta para o `prompt_version_id`
  com o texto exato; reprodutibilidade trivial; diff é `difflib.unified_diff(a.text, b.text)`.
- **Sacrificamos:** redundância de armazenamento entre versões similares. Aceitável:
  prompts são pequenos, e o domínio premia clareza sobre economia.
- **A revisitar ao escalar.** Se prompts viraram artefatos enormes (RAG context com
  milhares de documentos inlined), considerar deduplicação por hash + tabela de blobs.

---

## ADR-3: Adapters de modelo — ABC + impls específicas

**Status:** Aceito · 2026-05-28

**Contexto.** Precisamos chamar provedores diferentes (Anthropic, OpenAI, Google, e um
`FakeAdapter` determinístico para CI/demo sem chave) com **mesma interface**, mas
extraindo deles informação que cada um expõe de jeito diferente: `usage.input_tokens`,
`usage.prompt_tokens`, `usage_metadata.input_token_count`, etc. A latência precisa ser
medida no nosso lado (porque latência de rede + processamento do cliente importam para
o produto). Custo é função do `usage` real × pricing da `ModelConfig`.

**Alternativas consideradas.**

- **A — Classe base `ModelAdapter` (ABC) + implementações por provedor (escolhido).**
  Cada subclasse adapta o SDK específico para o contrato `ModelAdapter.call`. Normaliza
  `usage`, mede latência localmente, retorna `ModelResponse` uniforme.
- **B — `dict[str, callable]`.** Funciona, mas não acomoda estado (cliente HTTP reusado,
  pool de conexões) sem closure feia. Tipagem fraca em Python; mypy reclama.
- **C — `litellm` como camada única.** Tira o trabalho da gente, mas tem opinião própria
  sobre normalização (e às vezes faz retries internos invisíveis). Mascara dados que
  queremos medir: o produto vende **medição rigorosa**.

**Decisão.** **Classe base `ModelAdapter` ABC** com método `async def call(system, user,
params) -> ModelResponse`. `ModelResponse` é um dataclass com `text, input_tokens,
output_tokens, latency_ms, raw`. Custo NÃO está no `ModelResponse` — fica numa camada
acima (`evaluation/cost.py`) que aceita `(response, model_config)`, para não acoplar
adapter à pricing-table.

Provedores implementados:
- `FakeAdapter` — determinístico, usado pelo seed e CI. Retorna outputs roteirizados
  por `(prompt_version, slice)` e tokens/latência simulados realistas.
- `ClaudeAdapter`, `OpenAIAdapter` — implementam o contrato chamando os SDKs oficiais.
- `GeminiAdapter` — stub que conforma à interface mas levanta `NotImplementedError`,
  pronto para plugar.

Seleção via env var `MODEL_PROVIDER` + per-`ModelConfig.provider`. Default: `fake`.

**Consequências.**
- **Ganhamos:** controle total sobre o que medimos; testes determinísticos via `FakeAdapter`;
  pode usar SDKs nativos onde tiverem features específicas (e.g., Anthropic `stream`).
- **Sacrificamos:** mais código por provedor do que `litellm`; precisamos manter a interface
  atualizada quando SDKs mudam.
- **A revisitar.** Se passar de 5+ provedores, considerar `litellm` por baixo da interface
  (não a interface inteira), mantendo nossa normalização por cima.

---

## ADR-4: Lógica de scoring — módulo puro + judge isolado

**Status:** Aceito · 2026-05-28

**Contexto.** A camada de avaliação é o coração do produto. Existem dois caminhos
intrínsecos: (a) checks determinísticos sobre output estruturado e (b) LLM-as-judge para
qualidades subjetivas. Precisa ser **testável** (cobertura > 80%) e **extensível** (adicionar
novo check sem editar o core).

**Alternativas consideradas.**

- **A — Módulo `evaluation/` com funções puras (checks) + serviço isolado (judge).**
  Cada check é `(output, expected, config) -> CheckResult`. Judge tem signature tipada
  (`RubricInputs → RubricOutputs`). Agregação é função pura de `EvalResult[] → Scorecard`.
- **B — Tudo dentro do worker.** Acopla orquestração com lógica; cada teste novo precisa
  subir o worker. Difícil de cobrir.
- **C — Regras em config YAML estilo `promptfoo`** + executor genérico. Atraente, mas
  YAML vira DSL ad-hoc — adicionar um check com lógica não-trivial exige sair do YAML
  pra Python, e aí o YAML é só boilerplate. Caminho que parece "low-code" e termina mais
  complicado.

**Decisão.** **Módulo `evaluation/` com funções puras + judge isolado atrás de interface.**

Estrutura:
- `evaluation/checks/`: registry de funções puras `(output, expected, config) -> CheckResult`.
  Adicionar um check novo = um arquivo + registro no `registry.py`. Sem mexer no core.
- `evaluation/judge.py`: classe `RubricJudge` com `RubricInputs` (task_description,
  test_case_input, candidate_output, rubric_criteria) e `RubricOutputs` (quality,
  instruction_adherence, factual_structural, tone_format, reasoning). Prompt do judge tem
  CoT explícito, many-shot anchors (bom/médio/ruim), e schema JSON estrito com 1 retry +
  marker `judge_error` em falha persistente.
- `evaluation/aggregate.py`: `aggregate(eval_results) -> Scorecard`. Função pura, sem I/O.
- `evaluation/regression.py`: `compare(baseline, candidate, thresholds) -> RegressionVerdict`.

O judge é a única parte com I/O externo (chama um LLM); fica atrás de uma interface
substituível por `FakeJudge` em testes.

**Consequências.**
- **Ganhamos:** cobertura de testes alta sem mock de SDK; novos checks são triviais;
  o módulo é portátil (pode virar lib reusável fora deste projeto).
- **Sacrificamos:** mais código que YAML "declarativo", mas o YAML é declarativo só até
  você precisar de lógica.
- **A revisitar.** Se aparecer pressão por permitir usuários definirem checks via UI sem
  escrever Python, considerar uma camada de config no topo (não substituindo o módulo,
  mas alimentando-o). O importante é que o core continua puro.
