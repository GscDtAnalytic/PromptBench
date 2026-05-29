"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Callout } from "@/components/callout";
import { RegressionVerdictPanel } from "@/components/regression-verdict";
import { SectionHeader } from "@/components/section-header";
import { api } from "@/lib/api";
import type {
  ComparisonResult,
  LeaderboardEntry,
  Task,
} from "@/lib/types";

export function CompareView() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [taskId, setTaskId] = useState<number | "">("");
  const [runs, setRuns] = useState<LeaderboardEntry[]>([]);
  const [baseline, setBaseline] = useState<number | "">("");
  const [candidate, setCandidate] = useState<number | "">("");
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listTasks().then(setTasks).catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!taskId) return;
    setResult(null);
    api
      .getLeaderboard(Number(taskId))
      .then((rs) => {
        setRuns(rs);
        // baseline = pior (último); candidate = melhor (primeiro)
        setBaseline(rs[rs.length - 1]?.eval_run_id ?? "");
        setCandidate(rs[0]?.eval_run_id ?? "");
      })
      .catch((e) => setError(String(e)));
  }, [taskId]);

  async function onCompare() {
    if (!baseline || !candidate) return;
    setError(null);
    try {
      const r = await api.compare(Number(baseline), Number(candidate));
      setResult(r);
    } catch (e) {
      setError(String(e));
    }
  }

  const baselineRun = useMemo(
    () => runs.find((r) => r.eval_run_id === Number(baseline)),
    [runs, baseline],
  );
  const candidateRun = useMemo(
    () => runs.find((r) => r.eval_run_id === Number(candidate)),
    [runs, candidate],
  );
  const taskName = useMemo(
    () => tasks.find((t) => t.id === Number(taskId))?.name,
    [tasks, taskId],
  );
  const sameRun =
    baseline !== "" && candidate !== "" && baseline === candidate;
  const ready = !!baseline && !!candidate && !sameRun;
  const noRunsForTask = taskId !== "" && runs.length < 2;

  return (
    <div className="space-y-2">
      <header className="space-y-3 mb-7">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-50 leading-tight">
          Comparar runs
        </h1>
        <Callout
          tone="muted"
          label="por que esta tela existe"
          className="max-w-2xl"
        >
          O score global pode subir enquanto um slice regride. Esta tela
          expõe isso com veredito por dimensão, slice e custo.
        </Callout>
      </header>

      <SectionHeader
        step={1}
        title="Selecionar runs"
        description="Mesma task. Baseline = versão estável; candidate = versão em teste."
      />
      <div className="mt-4 rounded-lg border border-slate-800 bg-slate-900/30 p-5 space-y-4">
        <div className="grid gap-3 md:grid-cols-3 items-end">
          <Select
            label="task"
            placeholder="Selecione uma task"
            value={taskId}
            onChange={(v) => setTaskId(v)}
            options={tasks.map((t) => ({ value: t.id, label: t.name }))}
          />
          <Select
            label="baseline"
            placeholder="Selecione uma baseline"
            value={baseline}
            onChange={(v) => setBaseline(v)}
            options={runs.map((r) => ({
              value: r.eval_run_id,
              label: `run #${r.eval_run_id} · v${r.version_number} · ${r.model_name} (${r.aggregate_score.toFixed(3)})`,
            }))}
          />
          <Select
            label="candidate"
            placeholder="Selecione um candidate"
            value={candidate}
            onChange={(v) => setCandidate(v)}
            options={runs.map((r) => ({
              value: r.eval_run_id,
              label: `run #${r.eval_run_id} · v${r.version_number} · ${r.model_name} (${r.aggregate_score.toFixed(3)})`,
            }))}
          />
        </div>
        <div className="flex items-end justify-between gap-3 pt-1">
          <div className="space-y-1">
            <p className="text-[11px] text-slate-500">
              Thresholds: dimensão −5%, slice −10%, custo +20%.
            </p>
            {noRunsForTask ? (
              <p className="text-[11px] text-amber-400 leading-snug">
                Esta task ainda não tem runs concluídos.{" "}
                <Link
                  href={`/tasks/${taskId}`}
                  className="underline underline-offset-2 hover:text-amber-300"
                >
                  Rode um experimento
                </Link>{" "}
                e volte aqui.
              </p>
            ) : sameRun ? (
              <p className="text-[11px] text-amber-400">
                Baseline e candidate são o mesmo run — escolha runs diferentes.
              </p>
            ) : ready ? (
              <p className="text-[11px] text-emerald-400 inline-flex items-center gap-1">
                <span aria-hidden>✓</span>
                Pronto para comparar.
              </p>
            ) : (
              <p className="text-[11px] text-slate-500">
                Selecione task, baseline e candidate.
              </p>
            )}
          </div>
          <Button
            variant="primary"
            onClick={onCompare}
            disabled={!ready}
            className={
              ready
                ? "ring-2 ring-sky-400/60 ring-offset-2 ring-offset-slate-950 shadow-lg shadow-sky-500/35 scale-[1.02] hover:scale-[1.04]"
                : ""
            }
          >
            Comparar →
          </Button>
        </div>
        {error && <div className="text-xs text-red-400">{error}</div>}
      </div>

      {!result && <VerdictExplainer />}

      {result && baselineRun && candidateRun && (
        <>
          <SectionHeader
            step={2}
            title="Veredito"
            description={`Comparando baseline #${result.baseline_run_id} (v${baselineRun.version_number} · ${baselineRun.model_name}) vs candidate #${result.candidate_run_id} (v${candidateRun.version_number} · ${candidateRun.model_name})${taskName ? ` na task "${taskName}"` : ""}.`}
          />
          <div className="mt-4">
            <RegressionVerdictPanel verdict={result.verdict} />
          </div>
        </>
      )}
    </div>
  );
}

function VerdictExplainer() {
  const items = [
    {
      key: "dimensão",
      title: "Dimensão",
      body: "Cada dimensão da rubrica (qualidade, instrução, factual, tom) não pode cair além do threshold.",
    },
    {
      key: "slice",
      title: "Slice",
      body: "Quebra por typical / edge / known_failure / adversarial. Média esconde regressão de edge case.",
    },
    {
      key: "custo",
      title: "Custo",
      body: "Custo por execução não pode subir além do permitido — qualidade igual a custo maior reprova.",
    },
  ];
  return (
    <div className="mt-3 rounded-lg border border-slate-800 bg-slate-900/20 p-5">
      <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-3">
        Como funciona o veredito
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {items.map((it, i) => (
          <div
            key={it.key}
            className="group rounded-md border border-slate-800/80 bg-slate-950/40 p-3 transition-colors hover:border-slate-700 hover:bg-slate-950/70"
          >
            <div className="flex items-baseline gap-2">
              <span className="text-[10px] font-mono text-slate-600 tabular-nums">
                {String(i + 1).padStart(2, "0")}
              </span>
              <div className="text-sm font-semibold text-slate-100">
                {it.title}
              </div>
            </div>
            <p className="mt-1 text-xs text-slate-400 leading-snug">
              {it.body}
            </p>
          </div>
        ))}
      </div>
      <div className="mt-4 text-[11px] text-slate-400 leading-snug">
        Veredito ={" "}
        <span className="font-mono text-slate-200">dimensão ∧ slice ∧ custo</span>.
        Reprova em qualquer uma bloqueia a promoção.
      </div>
    </div>
  );
}

function Select({
  label,
  placeholder,
  value,
  onChange,
  options,
}: {
  label: string;
  placeholder: string;
  value: number | "";
  onChange: (v: number | "") => void;
  options: { value: number; label: string }[];
}) {
  const filled = value !== "";
  return (
    <label className="block">
      <div className="text-[11px] uppercase tracking-wide text-slate-400 mb-1">
        {label}
      </div>
      <div className="relative">
        <select
          value={value}
          onChange={(e) =>
            onChange(e.target.value ? Number(e.target.value) : "")
          }
          className={
            "w-full cursor-pointer rounded-md border bg-slate-950 pl-2.5 pr-7 py-1.5 text-sm appearance-none transition-colors focus:outline-none focus:ring-1 focus:ring-sky-500/40 " +
            (filled
              ? "border-slate-600 text-slate-100 hover:border-sky-600/60 focus:border-sky-500/70"
              : "border-slate-800 text-slate-500 hover:border-slate-600 hover:text-slate-300 focus:border-sky-500/70")
          }
        >
          <option value="">{placeholder}</option>
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <span className="pointer-events-none absolute inset-y-0 right-2 flex items-center text-slate-500">
          <svg width="10" height="6" viewBox="0 0 10 6" fill="none">
            <path d="M1 1l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
      </div>
    </label>
  );
}
