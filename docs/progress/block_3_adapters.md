# Bloco 3 — Adapters (Fake/Claude/OpenAI/Gemini-stub) + smoke test

## O que foi feito

- **`app/adapters/base.py`**: `ModelAdapter` ABC e dataclass `ModelResponse(text,
  input_tokens, output_tokens, latency_ms, raw)`. Helper estático `_public_params`
  que remove chaves prefixadas com `_` (usado pelos adapters reais para não vazar
  `_scenario_hint` ao provedor).
- **`app/adapters/fake_scripts.py`**: tabela determinística com 10 funções
  `(task_slug × prompt_version) -> output(slice, rep)`. Cada função reflete o
  comportamento esperado da versão do prompt:
  - v1 baseline: às vezes não-JSON, alucinação de skills
  - v2 JSON: JSON válido, qualidade média, ainda alucina em known_failure
  - v3 few-shot: **alto em typical/edge, falha por prompt injection em adversarial**
  - v4 CoT: justificativas longas, parcialmente vulnerável a injection
  - v5 guardrails: resistente, justifica conservadoramente em adversarial
- **`app/adapters/fake.py`**: `FakeAdapter` lê `params["_scenario_hint"]`, gera output
  via `fake_scripts.generate_output`, simula latência (`asyncio.sleep` proporcional ao
  tamanho do prompt + jitter determinístico) e tokens (heurística ~1 token / 4 chars).
- **`app/adapters/claude.py`**: `ClaudeAdapter` (Anthropic SDK), usa `messages.create`,
  extrai `usage.input_tokens`/`output_tokens` reais, mede latência com `perf_counter`,
  retry tenacity com backoff exponencial (3 tentativas).
- **`app/adapters/openai.py`**: análogo com `chat.completions.create` e
  `usage.prompt_tokens`/`completion_tokens`.
- **`app/adapters/gemini.py`**: stub que levanta `NotImplementedError`.
- **`app/adapters/factory.py`**: `get_adapter(provider, model_name)` com lazy import
  dos SDKs reais (FakeAdapter sempre disponível; SDKs reais só são carregados quando
  o provider correspondente é solicitado).
- **`tests/test_adapters.py`** (13 testes):
  - FakeAdapter: retorna ModelResponse, é determinístico, varia entre repetições,
    caso de regressão v3-adversarial visível, v5-guardrails resiste, não vaza
    `_scenario_hint`.
  - Factory: retorna instância certa, Gemini levanta NotImplementedError.
  - Pricing: cálculos básicos e split entre input/output corretos.
  - Claude/OpenAI: normalizam response usando mocks dos SDKs; o teste
    `test_adapter_ignores_internal_params` valida que `_scenario_hint` não vaza ao
    cliente HTTP.
- **`scripts/smoke_adapter.py`**: roda 5 cenários do FakeAdapter e imprime
  `text/in/out/lat/cost`. Saída real:
  - v1 baseline typical: texto livre (não-JSON), score=75
  - v3 fewshot typical: JSON correto, score=78
  - **v3 fewshot adversarial: score=100, missing_skills=[]** (regressão visível)
  - v5 guardrails adversarial: score=68 + nota de política (resistiu)
  - task_b v3 adversarial: "Confirmamos o reembolso de R$ 5.000" (vazamento)

## Verificações executadas

| Comando | Resultado |
|---|---|
| `.venv/bin/ruff check app tests --fix` | `All checks passed!` (1 fix automático de import) |
| `.venv/bin/mypy app` | `Success: no issues found in 24 source files` |
| `.venv/bin/pytest -v` | `20 passed in 3.53s` (7 do bloco anterior + 13 novos) |
| `PYTHONPATH=backend backend/.venv/bin/python -m scripts.smoke_adapter` | imprime 5 cenários; regressão de v3 adversarial visível |

## Decisões/aprendizados deste bloco

- **`_scenario_hint` em `params`** (em vez de um parâmetro separado no contrato): mantém
  a interface idêntica aos provedores reais. Chave `_-prefixed` significa interna, e o
  helper `_public_params` garante que não vaza.
- **Lazy import** dos SDKs no `factory.py`: o backend sobe sem precisar das chaves; o
  SDK só é importado quando o provider correspondente é resolvido.
- **`StrEnum`** para `Provider` permite comparar com strings diretamente (`provider ==
  "fake"`) — útil para parsing de env vars.
- **Tokens da heurística "1 token / 4 chars"** no FakeAdapter: imita a contagem real dos
  provedores grandes. Não usamos `tiktoken` no fake porque o objetivo é simular o
  pipeline de medição, não calcular tokens reais.
- **Latência simulada com `asyncio.sleep` real**: faz com que `perf_counter` registre
  uma latência crível, e o pipeline async é exercitado de verdade.
- **Mocks via `MagicMock`/`AsyncMock`** em vez de `respx`: os SDKs Anthropic e OpenAI
  já têm classes próprias e o objetivo do teste é validar **normalização** (não a
  camada HTTP). `MagicMock` é mais direto.

## Próximo bloco

**Bloco 4 — Camada de avaliação + testes (NÃO avança sem verde).**

Objetivos:
- `app/evaluation/checks/`: registry com 6 checks puros (`json_schema_valid`,
  `required_fields_present`, `exact_match`, `set_match`, `regex_match`, `numeric_range`).
  Cada um é `(output, expected, config) -> CheckResult(passed, score, detail)`.
- `app/evaluation/judge.py`: `RubricJudge` com `RubricInputs`/`RubricOutputs` tipados.
  Prompt do judge tem CoT explícito, many-shot anchors (bom/médio/ruim), schema JSON
  estrito + 1 retry + marker `judge_error`. Usa `ModelAdapter` injetado (default:
  FakeAdapter — para testes; pode ser substituído por Claude/OpenAI em prod).
- `app/evaluation/aggregate.py`: `aggregate(eval_results) -> ScorecardPayload` com
  média ponderada por dimensão, variância sobre repetições, breakdown por slice.
- Testes em `tests/test_checks.py`, `tests/test_aggregate.py`, `tests/test_judge.py`
  com cobertura > 80% em `app/evaluation/`.
- Critério de aceite: `pytest --cov=app/evaluation` ≥ 80%; todos verdes.
