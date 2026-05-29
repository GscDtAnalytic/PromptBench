# Bloco 7 — Mecanismo de regressão + testes

## O que foi feito

### Refinamento de `app/evaluation/regression.py`

(Esqueleto havia sido criado no Bloco 6.) Mecanismo `compare_runs(baseline, candidate,
thresholds) -> RegressionVerdictPayload`:

- Para cada dimensão (quality, instruction_adherence, factual_structural, tone_format):
  - delta absoluto na escala 1-5
  - falha se cair mais que `max_dimension_regression × 5` (default 0.05 × 5 = 0.25)
- Para cada slice (typical/edge/known_failure/adversarial):
  - delta absoluto na escala 0-1
  - falha se cair mais que `max_slice_regression` (default 0.10)
  - SLICE PRESENTE no baseline mas AUSENTE no candidate → tratado como 0
    (= regressão completa); inverso (slice novo no candidate) é OK.
- Custo: `(cand - base)/|base|`; falha se exceder `max_cost_increase` (default 0.20).
- Veredito é `passed = (len(failures) == 0)`.

### `tests/test_regression.py` (10 testes)

Casos cobertos:
- runs idênticos → `passed=True`, `failures=[]`
- candidate estritamente melhor → `passed=True`
- **CASO ÂNCORA**: candidate melhora typical mas regride 0.40 em adversarial →
  `passed=False` com `"adversarial" in failures`
- dimensão factual_structural caindo 0.5 → falha
- custo +100% → `cost_passed=False`
- custo igual → `cost_passed=True`
- breakdown expõe count sem alterar (sanity)
- slice novo no candidate (ausente no baseline) → passa
- slice presente no baseline removido no candidate → falha
- baseline com custo 0 → `cost_delta_pct=0.0` (sem ZeroDivision)

## Verificações executadas

| Comando | Resultado |
|---|---|
| `.venv/bin/ruff check app tests` | All checks passed! |
| `.venv/bin/mypy app` | Success in 56 source files |
| `.venv/bin/pytest --cov=app/evaluation` | **77 passed in 5.48s** |
| Cobertura `regression.py` | **100%** |
| Cobertura agregada `app/evaluation/` | **87%** |

## Decisões/aprendizados deste bloco

- **`FakeSC` (stand-in leve no teste)**: o `compare_runs` só usa `getattr`, então um
  duck-type simples basta. Evita ter que instanciar SQLAlchemy + commit.
- **Tratamento de "slice removido"**: explicitamente trata como `0.0` no candidate.
  Decisão intencional: se uma versão do prompt deixa de cobrir um slice, é regressão
  (você está reduzindo a superfície de validação).
- **Threshold absoluto vs percentual**: para dimensões usei `max × 5` (1-5 → escala 5),
  para slices usei o threshold direto (já em 0-1). É **explícito no código** para
  evitar confusão.
- **Cost delta vs cost absolute**: usamos %. Faz sentido — ir de $0.001 para $0.002 é
  100% mas absolutamente nada; o usuário escolhe o threshold relativo.
- **Os 13% de cobertura faltantes** ficam em `render.py` (helper trivial) e
  `task_checks.py` (configuração estática). Esses são exercitados de verdade pelo
  worker E2E no Bloco 9. Acima do alvo de 80%.

## Próximo bloco

**Bloco 8 — Frontend Next.js (telas 1-4 + export).**

Objetivos:
- `npx create-next-app` (TypeScript, Tailwind, App Router, ESLint).
- `npx shadcn@latest init` + componentes: button, card, table, badge, dialog.
- `frontend/lib/api.ts`: client tipado para todos os endpoints; `frontend/lib/types.ts`
  com tipos espelhados (incluindo `RegressionVerdictPayload`).
- Telas:
  1. `/tasks/[id]/page.tsx`: lista PromptVersions + botão "Rodar experimento"
     (modal escolhe ModelConfig + repetitions).
  2. `/runs/[id]/page.tsx`: status (polling) + scorecard com Recharts (radar).
  3. `/compare/page.tsx`: seleciona 2 runs, mostra delta-table colorida + badge
     `APROVADO`/`REPROVADO` com lista de failures.
  4. Slice breakdown integrado na tela 2.
  5-7. (se tempo permitir): diff viewer, leaderboard, export buttons.
- `frontend/Dockerfile`.
- Critério de aceite: `npm run lint` + `tsc --noEmit` verdes; navega ponta a ponta
  no docker-compose; tela 3 mostra veredito do caso de regressão âncora vermelho.
