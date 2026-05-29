import Link from "next/link";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { RubricCard } from "@/components/rubric-card";
import { SectionHeader } from "@/components/section-header";
import { SLICE_FILL, SLICE_ORDER } from "@/lib/slice-style";
import { RunExperimentForm } from "./run-experiment-form";
import type { SliceLabel } from "@/lib/types";

const STRATEGY_LABEL: Record<string, string> = {
  baseline: "baseline",
  json: "json",
  fewshot: "few-shot",
  cot: "CoT",
  guardrails: "guardrails",
};

const STRATEGY_DESC: Record<string, string> = {
  baseline: "Instrução solta, sem formato — referência para medir tudo.",
  json: "Exige saída JSON estrita conforme o contrato da task.",
  fewshot: "Inclui exemplos input → output para ancorar a saída.",
  cot: "Força raciocínio passo-a-passo antes da resposta final.",
  guardrails: "Restringe alucinação, valida enums e recusa fora-do-escopo.",
};

function strategyKey(name: string): string {
  const m = name.match(/^v\d+_(.+)$/);
  return m ? m[1] : name;
}
function strategyLabel(name: string): string {
  const k = strategyKey(name);
  return STRATEGY_LABEL[k] ?? k;
}
function strategyDesc(name: string): string | undefined {
  return STRATEGY_DESC[strategyKey(name)];
}

export default async function TaskPage({
  params,
}: {
  params: { id: string };
}) {
  const taskId = Number(params.id);
  const [task, prompts, testcases, modelConfigs, leaderboard, rubric] = await Promise.all([
    api.getTask(taskId),
    api.listPrompts(taskId),
    api.listTestCases(taskId),
    api.listModelConfigs(),
    api.getLeaderboard(taskId).catch(() => []),
    api.getRubric(taskId).catch(() => null),
  ]);

  const slices = testcases.reduce<Record<string, number>>((acc, tc) => {
    acc[tc.slice] = (acc[tc.slice] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-2">
      <header className="space-y-2 mb-7">
        <div className="flex items-center gap-2">
          <Link
            href="/"
            className="text-xs text-slate-500 hover:text-slate-300 focus-visible:outline-none focus-visible:text-slate-300"
          >
            ← tasks
          </Link>
          <Badge variant="muted">{task.task_type}</Badge>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-slate-50 leading-tight">
          {task.name}
        </h1>
        <p className="text-sm text-slate-400 max-w-2xl leading-relaxed">
          {task.description}
        </p>
      </header>

      {/* 01 Dataset */}
      <SectionHeader
        step={1}
        title="Dataset"
        description={`${testcases.length} casos, distribuídos por slice.`}
      />
      <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-2">
        {SLICE_ORDER.map((s) => {
          const n = slices[s] || 0;
          const total = testcases.length || 1;
          return (
            <div
              key={s}
              className="rounded-md border border-slate-800 bg-slate-900/40 p-3 transition-colors hover:border-slate-700 hover:bg-slate-900/70"
            >
              <div className="flex items-center gap-2">
                <span
                  className="inline-block w-2 h-2 rounded-full"
                  style={{ background: SLICE_FILL[s as SliceLabel] }}
                />
                <span className="text-xs text-slate-300">{s}</span>
              </div>
              <div className="mt-1 flex items-baseline gap-1.5">
                <span className="font-mono text-lg text-slate-100">{n}</span>
                <span className="text-[11px] text-slate-500">
                  ({Math.round((n / total) * 100)}%)
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* 02 Rubrica */}
      {rubric && (
        <>
          <SectionHeader
            step={2}
            title="Rubrica"
            description="4 dimensões, pesos por task, âncoras 1–5."
          />
          <div className="mt-4">
            <RubricCard rubric={rubric} />
          </div>
        </>
      )}

      {/* 03 Versionamento */}
      <SectionHeader
        step={3}
        title="Versões de prompt"
        description="Imutáveis. Cada edição cria uma nova versão — progressão deliberada baseline → guardrails."
      />
      <div className="mt-4 grid gap-2">
        {prompts.map((p, i) => {
          const label = strategyLabel(p.name);
          const desc = strategyDesc(p.name);
          const params = p.model_params as Record<string, unknown>;
          const progress = prompts.length > 1 ? i / (prompts.length - 1) : 0;
          return (
            <div
              key={p.id}
              className="group relative flex items-start justify-between gap-4 rounded-md border border-slate-800 bg-slate-900/30 p-3 pl-4 text-sm transition-colors hover:border-slate-700 hover:bg-slate-900/60 active:bg-slate-900/80"
            >
              <span
                aria-hidden
                className={
                  "absolute left-0 top-2 bottom-2 w-[3px] rounded-full transition-opacity " +
                  (p.is_baseline ? "bg-amber-500/70" : "bg-sky-500/70 group-hover:bg-sky-400/80")
                }
                style={
                  p.is_baseline
                    ? undefined
                    : { opacity: 0.3 + progress * 0.7 }
                }
              />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm text-slate-100 tabular-nums">
                    v{p.version_number}
                  </span>
                  <span className="text-slate-700">/</span>
                  <span className="text-xs uppercase tracking-wide text-slate-200 font-semibold">
                    {label}
                  </span>
                </div>
                {desc && (
                  <p className="mt-1.5 text-xs text-slate-300 leading-snug">
                    {desc}
                  </p>
                )}
                <div className="text-[11px] text-slate-700 mt-2.5 font-mono transition-colors group-hover:text-slate-500">
                  temp={String(params.temperature ?? "0")} · max_tokens=
                  {String(params.max_tokens ?? "—")}
                </div>
              </div>
              <div className="flex flex-col items-end gap-1 pt-0.5">
                {p.is_baseline ? (
                  <Badge variant="warning">baseline</Badge>
                ) : (
                  <span className="text-[10px] font-mono text-slate-700 tabular-nums">
                    {i + 1}/{prompts.length}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* 04 Executar experimento */}
      <SectionHeader
        step={4}
        title="Rodar experimento"
        description="N repetições do dataset para estimar variância. Use 3+."
      />
      <div className="mt-4 rounded-lg border border-sky-900/30 bg-sky-950/20 p-5">
        <RunExperimentForm
          taskId={taskId}
          prompts={prompts}
          modelConfigs={modelConfigs}
        />
      </div>

      {/* 05 Leaderboard */}
      <SectionHeader
        step={5}
        title="Leaderboard"
        description="Runs concluídos por score. Empate técnico → escolha o mais barato."
      />
      <div className="mt-4">
        {leaderboard.length === 0 ? (
          <div className="rounded-md border border-dashed border-slate-800 bg-slate-900/30 p-6 text-center text-xs text-slate-400">
            Nenhum scorecard ainda.{" "}
            <span className="text-slate-500">
              Rode um experimento acima — ele aparece aqui assim que concluir.
            </span>
          </div>
        ) : (
          <div className="overflow-hidden rounded-md border border-slate-800">
            <table className="w-full text-xs">
              <thead className="bg-slate-900/60 text-slate-400 text-[11px] uppercase tracking-wide">
                <tr>
                  <th className="text-left px-3 py-2 font-medium">prompt</th>
                  <th className="text-left px-3 py-2 font-medium">modelo</th>
                  <th className="text-right px-3 py-2 font-semibold text-slate-300">
                    score
                  </th>
                  <th className="text-right px-3 py-2 font-medium">lat</th>
                  <th className="text-right px-3 py-2 font-medium">custo</th>
                  <th className="text-right px-3 py-2 font-medium">fail</th>
                  <th className="px-3 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.map((e) => (
                  <tr
                    key={e.eval_run_id}
                    className="group border-t border-slate-800/60 transition-colors hover:bg-slate-900/50"
                  >
                    <td className="px-3 py-2.5 font-mono text-slate-200">
                      v{e.version_number}{" "}
                      <span className="text-slate-600">·</span>{" "}
                      <span className="text-slate-400">
                        {e.prompt_version_name}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-slate-300">
                      {e.model_name}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono text-slate-50 font-semibold tabular-nums">
                      {e.aggregate_score.toFixed(3)}
                    </td>
                    <td className="px-3 py-2.5 text-right text-slate-400 tabular-nums">
                      {Math.round(e.avg_latency_ms)}ms
                    </td>
                    <td className="px-3 py-2.5 text-right text-slate-400 tabular-nums">
                      ${e.total_cost_usd.toFixed(4)}
                    </td>
                    <td
                      className={`px-3 py-2.5 text-right tabular-nums ${
                        e.failure_rate > 0.1
                          ? "text-red-400"
                          : "text-slate-400"
                      }`}
                    >
                      {(e.failure_rate * 100).toFixed(0)}%
                    </td>
                    <td className="px-3 py-2 text-right">
                      <Link
                        href={`/runs/${e.eval_run_id}`}
                        className="group/ver inline-flex items-center rounded px-2 py-1 text-sky-400 transition-all duration-100 hover:bg-sky-500/15 hover:text-sky-200 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-sky-500/50 focus-visible:ring-offset-1 focus-visible:ring-offset-slate-950"
                      >
                        ver{" "}
                        <span
                          aria-hidden
                          className="ml-0.5 transition-transform group-hover/ver:translate-x-1"
                        >
                          →
                        </span>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
