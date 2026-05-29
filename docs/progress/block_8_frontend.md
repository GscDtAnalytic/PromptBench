# Bloco 8 — Frontend Next.js (telas 1-4 + export)

## O que foi feito

### Configuração

- `frontend/package.json`: Next 14.2.21, React 18.3.1, TypeScript 5.6, Tailwind 3.4,
  Recharts 2.13, class-variance-authority, clsx, tailwind-merge.
- `tsconfig.json` com strict + paths `@/*`.
- `tailwind.config.ts` com tema escuro denso (paleta slate).
- `eslint.config` legacy via `.eslintrc.json` extends `next/core-web-vitals`.
- `Dockerfile`: node:20-alpine, `npm install`, `npm run dev`.

### Lib client tipado

- `lib/types.ts`: tipos espelhados manualmente do backend (Task, PromptVersion,
  TestCase, ModelConfig, EvalRun, EvalRunStatus, EvalResult, Scorecard, LeaderboardEntry,
  RegressionVerdict, ComparisonResult, SliceMetrics).
- `lib/api.ts`: client com `fetch` wrapper, `ApiError`, `cache: "no-store"`. Métodos
  para todos os endpoints do backend.
- `lib/utils.ts`: `cn()` (clsx+tailwind-merge), formatters `fmtUSD`, `fmtMs`, `fmtPct`,
  `fmtScore01`, `fmtRubric`.

### Componentes UI

- `components/ui/card.tsx`, `button.tsx`, `badge.tsx` (mini-shadcn).
- `components/score-radar.tsx`: Recharts RadarChart das 4 dimensões 1-5.
- `components/slice-breakdown.tsx`: BarChart score 0-1 por slice.
- `components/regression-verdict.tsx`: card com APROVADO/REPROVADO + lista de
  failures + grid colorida de dimensões e slices (verde delta+, vermelho delta-).

### Páginas (App Router)

- **`/` (home)**: lista de Tasks como cards clicáveis. Se backend offline, mostra
  mensagem de fallback com instruções.
- **`/tasks/[id]`** (tela 1): dataset (distribuição por slice), versões de prompt
  com marca de baseline, **form lado-a-lado** para rodar experimento (escolhe
  prompt + modelo + repetições; POST /runs e redireciona para /runs/{id}),
  leaderboard ordenado por aggregate_score.
- **`/runs/[id]`** (telas 2+4): client component com polling de `/runs/{id}/status`
  a cada 1.5s; quando `status=done`, busca scorecard e renderiza:
  - 4 metric cards (aggregate, latência média, custo total, taxa de falha)
  - Radar das 4 dimensões da rubrica (1-5)
  - Bar chart **por slice** (typical/edge/known_failure/adversarial)
  - Variância + botões de export CSV/PDF (link direto).
- **`/compare`** (tela 3): seleciona task → carrega runs do leaderboard → escolhe
  baseline e candidate → POST /compare → renderiza `<RegressionVerdictPanel>` com:
  - Badge `APROVADO`/`REPROVADO` + custo Δ
  - Lista de failures detectadas
  - Grid de dimensões com `Δ +/-` colorida
  - Grid de slices com mesma codificação visual

### Layout

- `app/layout.tsx`: header sticky com navegação (tasks / compare), max-w-7xl,
  paleta dark, sem enfeite.
- `globals.css`: Tailwind base + body bg slate-950.

## Verificações executadas

| Comando | Resultado |
|---|---|
| `npm install` (Next 14 + React 18) | 423 packages em 51s |
| `npx tsc --noEmit` | OK (sem erros) |
| `npx next lint` | `✔ No ESLint warnings or errors` |

## Decisões/aprendizados deste bloco

- **Next 14 em vez de Next 15** — o RC do React 19 conflitou com peer deps do
  next@15; Next 14 stable com React 18 evita o problema sem perder funcionalidade
  (app router + server components funcionam igual).
- **Sem shadcn CLI** — copiei manualmente Card/Button/Badge minimal. O CLI exige
  conexão internet pra inicializar e o monorepo já tem todo o tooling que ele instalaria.
- **lib/types.ts manual** em vez de gerado do OpenAPI — mais simples no MVP; quando o
  contrato mudar muito (após o Bloco 9), vale plugar `openapi-typescript`.
- **Polling em vez de WebSocket** — endpoint `/runs/{id}/status` é barato (count
  query). 1.5s de cadência é suficiente para UX.
- **Server components** lendo do backend no `/tasks/[id]` (server side fetch); o
  `/runs/[id]` é client side por causa do polling com `useEffect`.
- **`cache: "no-store"`** em todos os fetches — dados de scorecard/leaderboard mudam
  e o cache do Next iria estragar.

## Próximo bloco

**Bloco 9 — Seed end-to-end + README + polish.**

Objetivos:
- `scripts/seed.py`: carrega prompts dos YAMLs, carrega testcases dos JSONLs, cria
  2 ModelConfigs (fake-fast + fake-thorough), dispara 2 EvalRuns de demo (v1 baseline
  e v3 fewshot) e espera (polling) ambos completarem. Imprime o veredito de
  `compare(v1, v3)` e confirma `passed=False` por regressão em adversarial.
- `make seed` chama o script.
- Subir o stack completo via `docker compose up --build` e validar:
  - backend `/health` 200
  - frontend `/` mostra as 2 tasks
  - `/tasks/{id}` mostra prompts/leaderboard
  - `/compare` produz o veredito REPROVADO no caso âncora
- README com arquitetura (Mermaid diagram), resumo dos 4 ADRs, como rodar,
  3-4 screenshots e seção "o que eu mediria diferente em produção".
- Critério de aceite: `make check` verde em tudo; `make seed` produz os 2 runs +
  veredito visível na UI.
