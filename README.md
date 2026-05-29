# PromptBench Studio

[![CI](https://github.com/GscDtAnalytic/PromptBench/actions/workflows/ci.yml/badge.svg)](https://github.com/GscDtAnalytic/PromptBench/actions/workflows/ci.yml)

🌐 **English** · [Português](README.pt-BR.md)

> **Unlike LangSmith or PromptLayer, PromptBench makes the regression verdict the primary output — not a dashboard metric you have to interpret.** The verdict is the conjunction `dimension ∧ slice ∧ cost`: failing any one blocks the promotion, regardless of the global average.

LLM applications regress in production when prompts change without control, and the
quality drop only surfaces after users complain. PromptBench Studio treats prompts as
software assets (versioned, measured, and compared with method) and makes regressions
detectable before deploy.

## What this project proves

- Treats prompts as immutable, auditable assets, with a history of who changed what and what the impact was.
- Builds datasets with evaluation slices (typical, edge, known_failure, adversarial) that expose real risks.
- Measures cost, latency, variance, and quality rigorously: tokens from the provider, standard deviation across repetitions, and a calibrated judge.
- Detects regressions before production with a per-dimension and per-slice verdict, not just the global average.

## Video demo

https://github.com/GscDtAnalytic/PromptBench/assets/demo.mp4

The video walks through the full flow: browsing tasks, opening the rubric, running an
experiment, reading the per-slice scorecard, and comparing two versions down to the
regression verdict. It shows both `fake` runs (deterministic, no API key) and real runs
on `claude-haiku-4-5`, side by side with real latency and cost.

> **No API key needed to run the demo.** The `FakeAdapter` produces deterministic,
> realistic outputs — including the adversarial regression case — so the full flow is
> visible without any external credentials.

---

> **How it works.** It runs multiple prompt versions across multiple models, measures
> quality, latency, and cost, and detects regressions that the global average hides by
> looking slice by slice (typical, edge, known_failure, adversarial).
>
> `PromptVersion` is immutable, variance is a first-class metric, cost comes from the
> provider's real `usage`, and the regression verdict approves or rejects a version by
> evaluating each slice individually.

---

## 1. Architecture on one page

```
                ┌────────────────────────┐
                │   Frontend (Next.js)   │
                │   App Router + TSX     │
                │   Recharts • Tailwind  │
                └───────────┬────────────┘
                            │  fetch (typed REST)
                            ▼
                ┌────────────────────────┐         ┌──────────────────┐
                │   Backend (FastAPI)    │ ──────▶ │  Postgres 16     │
                │   Pydantic v2          │         │  (7 entities)    │
                │   SQLAlchemy 2.0       │         └──────────────────┘
                └───────────┬────────────┘
                            │  enqueue
                            ▼
                ┌────────────────────────┐         ┌──────────────────┐
                │   Worker (arq)         │ ──────▶ │  Redis           │
                │   run_eval_run(run_id) │         └──────────────────┘
                └───────────┬────────────┘
                            │ calls
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
        │   │ (pure)   │ (LLM-judge) │ + variance│  │
        │   └──────────┴─────────────┴──────────┘   │
        │   ┌──────────────────────────────────┐    │
        │   │  regression.compare_runs         │    │
        │   │  (verdict by dim+slice+cost)     │    │
        │   └──────────────────────────────────┘    │
        └───────────────────────────────────────────┘
```

### The 7 entities

`Task` · `PromptVersion` (immutable) · `TestCase` (with `slice`) · `ModelConfig`
(with pricing) · `EvalRun` (status + repetitions) · `EvalResult` (raw_output,
latency, tokens, cost, deterministic_scores, rubric_scores) · `Scorecard`
(4 dimensions + cost + latency + variance + `per_slice_breakdown`).

### The 4 architectural decisions (ADR summary)

| # | Decision | Short rationale |
|---|---|---|
| ADR-1 | **arq** (async-native, Redis) as the worker | FastAPI is async-first; Celery is overkill for the MVP; BackgroundTasks dies with the process. |
| ADR-2 | **PromptVersion = immutable snapshot** | The product sells auditable immutability; storing the string is cheap; the diff is trivial on read. |
| ADR-3 | **`ModelAdapter` ABC + per-provider implementations** | Each provider exposes `usage` differently; we want to measure latency locally and cost from the pricing table; litellm masks that data. |
| ADR-4 | **Pure evaluation module + isolated judge** | Testability of the system's core; checks as pure functions; adding a new check is 1 file, with no changes to the core. |

Full details in [`docs/ADR.md`](docs/ADR.md).

---

## 2. Screens

### Tasks (home)

Each task exposes its prompt versions, the dataset by slice, and recent runs. The recent
activity already shows real runs on `claude-haiku-4-5` next to the `fake` runs.

![Tasks](docs/screenshots/tasks-home.png)

### Task detail

Dataset with slice distribution (60/20/10/10), a rubric whose 4 dimensions are scored
independently, and prompt versions v1 to v5 in a deliberate progression.

![Task detail](docs/screenshots/task-detail.png)

### Rubric contract and calibration anchors

The judge's full contract: task description, per-dimension criteria, and many-shot
anchors (good, average, bad) that calibrate the 1–5 scale.

![Rubric anchors](docs/screenshots/rubric-anchors.png)

### Run experiment and leaderboard

Fires N repetitions of the dataset to estimate variance. The leaderboard ranks completed
runs by score, with latency, real cost, and failure rate side by side; a technical tie
is broken by the cheapest option.

![Leaderboard](docs/screenshots/leaderboard.png)

### Run scorecard

Run KPIs (aggregate score, mean latency, total cost, failure rate), a radar of the 4
rubric dimensions with the variance (σ) across repetitions, and the score per slice. The
regression verdict reads the per-slice bars, not the average.

![Run scorecard](docs/screenshots/run-scorecard.png)

### Judge samples

LLM-as-judge transparency: for each sample, the per-dimension scores and the field-by-field
reasoning that justifies each score with evidence from the output.

![Judge samples](docs/screenshots/judge-samples.png)

### Compare runs

Verdict by dimension, slice, and cost. The global score can rise while a slice regresses
or while cost blows the budget, and this screen exists to expose that. Two real
comparisons on `claude-haiku-4-5`:

**Rejected.** Candidate v4 scores higher overall (0.936 vs 0.896) and improves most
slices, but the verdict rejects it because cost rose 89.3% against the +20% limit. A
better average does not earn promotion when it breaks the cost budget.

![Compare runs, rejected verdict](docs/screenshots/compare-rejected.png)

**Approved.** The same candidate v4 (0.936) against the naive v1 baseline (0.000): every
dimension and slice improves and cost even drops 3.3%. Safe to promote.

![Compare runs, approved verdict](docs/screenshots/compare-approved.png)

The verdict is the conjunction `dimension ∧ slice ∧ cost`: failing any one blocks the
promotion.

---

## 3. How to run

### Requirements
- Docker + Docker Compose.
- Anthropic/OpenAI keys are optional. The MVP runs without them: the deterministic
  `FakeAdapter` produces realistic scripted outputs, including the adversarial regression
  case. To use real providers, copy `.env.example` to `.env` and fill in the keys. Claude
  is already integrated and runs live.

### Bring everything up

```bash
docker compose up --build       # postgres + redis + backend + worker + frontend
```

Once the services are up (a few seconds), apply the migration and seed the demo data:

```bash
make migrate.up
make seed
```

`make seed` creates 2 Tasks, 60 TestCases (30 per task in a 60/20/10/10 distribution),
10 PromptVersions (5 per task, v1 baseline through v5 guardrails), 2 ModelConfigs
`fake-fast` and `fake-thorough`, and runs 4 demo EvalRuns (v1 and v3 for each task)
producing Scorecards and the anchor regression case.

Open:
- **Frontend**: http://localhost:3000
- **Backend (OpenAPI)**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

### Other useful commands (Makefile)

```bash
make help                # list all targets
make test                # pytest on the backend
make test.scoring        # only the evaluation layer tests, with coverage
make lint                # ruff
make typecheck           # mypy strict
make check               # lint + typecheck + test, backend and frontend
make validate-datasets   # check the JSONL and the slice distribution
make migrate.new name="description"   # create a new migration
```

### Run outside docker

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

## 4. What makes this different from a CRUD

### a) Prompts are versioned assets, no exceptions

There is no `UPDATE` on `prompt_versions`. Editing means a `POST` that creates a new
version with `version_number = max+1` in an atomic transaction. Every `EvalResult` points
to the exact `prompt_version_id` that produced it, which guarantees full reproducibility.

### b) Variance is a first-class metric

Each EvalRun runs `repetitions >= 3` per test_case. The Scorecard exposes the mean
standard deviation across repetitions. Non-deterministic output requires this: reporting
a mean without the deviation is a half-truth.

### c) The global score never hides a slice regression

Every comparison breaks down by `typical`, `edge`, `known_failure`, and `adversarial`.
The regression mechanism (`evaluation/regression.py`) applies thresholds per slice, not
only on the average. A real example produced by `make seed`:

```
task_a_resume_matching:
  v1 aggregate=0.467  v3=0.750     # v3 improved on average
  verdict: REJECTED                # but it fails in the detail:
    - dimension 'factual_structural' dropped -0.30 (limit -0.25)
    - slice 'adversarial' regressed -0.167 (limit -0.100)
    - cost rose 179.3% (limit +20.0%)
```

The average went up and the verdict rejected it. That is the point of the product.

### d) Cost and tokens come from the provider's real response

No adapter estimates tokens. The Anthropic/OpenAI SDK reports `usage`, and cost is
`usage × ModelConfig.price_per_1m_*` computed in `core/pricing.compute_cost_usd` with
`Decimal` (6 decimal places, because LLMOps bills on it).

### e) The judge does not invent scores

`RubricJudge` validates strict JSON (4 dimensions from 1 to 5 + reasoning), retries once
on a parse error, and on persistent failure propagates `judge_error` without filling in a
default. The judge prompt uses field-by-field CoT, many-shot anchors (good, average,
bad), and an explicit anti-halo instruction.

### f) Deterministic checks are pure functions

`evaluation/checks/` has 6 registrable checks (`json_schema_valid`,
`required_fields_present`, `exact_match`, `set_match`, `regex_match`, `numeric_range`),
each with the same signature `(output, expected, config) -> CheckResult`. Adding a new
check is 1 file + 1 line in the registry. Test coverage of the `evaluation/` module is
87%.

---

## 5. The 2 tasks

### Task A — Resume × Job Matching (`structured_extraction`)
- Input: `{resume_text, job_description}`
- Expected output: JSON `{match_score, matched_skills, missing_skills, ranking_justification}`
- Target risk: hallucinating skills that are not in the source text; prompt injection in
  `resume_text` inflating `match_score`.

### Task B — Customer Support (`classification_response`)
- Input: `{customer_message, account_context}`
- Expected output: JSON `{category, priority, suggested_reply, requires_human}`
- Target risk: a category outside the enum; an improper refund promise (customer
  injection); leaking data from other accounts.

Each task has 30 cases in JSONL, in a 60% typical, 20% edge, 10% known_failure, 10%
adversarial distribution. There are 5 prompt versions in YAML, in a deliberate
progression: v1 naive baseline, v2 JSON, v3 few-shot, v4 CoT, v5 guardrails.

---

## 6. What I would measure differently in production

The MVP delivers the experiment → measure → compare → gate cycle. In production, I would
add:

1. **Judge calibration against human labels.** Annotate 50 to 100 cases by hand and
   measure the correlation (Spearman/Kendall) between the judge and the human annotation,
   per dimension. Without calibration, the judge is a ruler with no zero point: it may be
   systematically lenient or strict.

2. **Multi-model judge with majority vote (or a jury).** Today it is 1 LLM. In production,
   running the same prompt across 3 different models (Claude, OpenAI, Gemini) and using
   the median or majority vote reduces the bias of a single provider.

3. **Continuous eval in production (drift).** Re-run the eval on sampled real traffic and
   compare it against the staging scorecard. Alert when the real-traffic slice diverges
   more than X% from synthetic-typical.

4. **Historical pricing tracking.** `ModelConfig.price` today is a snapshot. In production,
   pricing has a versioned history. Re-running an old experiment with the new price should
   stay reproducible.

5. **Auto-classification of slices for new test cases.** Slices today are annotated by
   hand. In production, a classifier (regex + LLM with confidence) would tag new cases
   arriving from traffic to feed the known_failure slice.

6. **Explicit injection success-rate metric.** Today a successful injection shows up
   indirectly (`match_score=100` + `missing=[]` in the adversarial slice). In production,
   this becomes an explicit check with a rate reported in the Scorecard.

7. **Output caching keyed on (prompt_version × test_case × model).** Re-running to
   generate new charts should not re-pay for tokens, only re-aggregate.

8. **PR check on GitHub Actions.** `compare_runs(baseline, candidate)` running
   automatically on PRs that touch `prompts/`, failing the build when the verdict is
   REJECTED. The mechanism already exists; only the CI glue is missing.

---

## 7. Build audit trail

Each build block has a file under `docs/progress/block_N_*.md` recording what was done,
the checks that ran (lint, typecheck, test), the non-obvious decisions, and the goal of
the next block. It is the reverse explanation of how the system was built.

---

*Part of [GSC Data portfolio](https://github.com/GscDtAnalytic) · also see [Pulso](https://github.com/GscDtAnalytic/Pulso) and [Mapear-RN](https://github.com/GscDtAnalytic/Mapear-RN)*
