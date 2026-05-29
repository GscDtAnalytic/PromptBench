"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { ModelConfig, PromptVersion } from "@/lib/types";

const selectCls =
  "w-full cursor-pointer rounded-md border border-slate-700 bg-slate-950 pl-2.5 pr-7 py-1.5 text-sm text-slate-200 appearance-none transition-colors hover:border-sky-600/50 hover:bg-slate-900 focus:outline-none focus:border-sky-500/60 focus:ring-1 focus:ring-sky-500/30";

const inputCls =
  "w-full rounded-md border border-slate-700 bg-slate-950 px-2.5 py-1.5 text-sm text-slate-200 transition-colors hover:border-sky-600/50 hover:bg-slate-900 focus:outline-none focus:border-sky-500/60 focus:ring-1 focus:ring-sky-500/30";

const VERSION_CONTEXT: Record<string, string> = {
  baseline: "linha-base ingênua",
  json: "JSON schema explícito",
  fewshot: "few-shot · exemplos i→o",
  cot: "CoT · raciocínio passo a passo",
  guardrails: "guardrails · anti-alucinação",
};

function promptOptionLabel(p: PromptVersion): string {
  const match = p.name.match(/^v\d+_(.+)$/);
  const ctx = match ? (VERSION_CONTEXT[match[1]] ?? null) : null;
  const base = p.is_baseline ? " ★" : "";
  return ctx
    ? `v${p.version_number} · ${ctx}${base}`
    : `v${p.version_number} — ${p.name}${p.is_baseline ? " ★" : ""}`;
}

function SelectWrapper({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative">
      {children}
      <span className="pointer-events-none absolute inset-y-0 right-2 flex items-center text-slate-500">
        <svg width="10" height="6" viewBox="0 0 10 6" fill="none">
          <path d="M1 1l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
    </div>
  );
}

export function RunExperimentForm({
  taskId,
  prompts,
  modelConfigs,
}: {
  taskId: number;
  prompts: PromptVersion[];
  modelConfigs: ModelConfig[];
}) {
  const router = useRouter();
  const [promptId, setPromptId] = useState<number | "">(
    prompts[0]?.id ?? "",
  );
  const [modelId, setModelId] = useState<number | "">(
    modelConfigs[0]?.id ?? "",
  );
  const [reps, setReps] = useState<number>(3);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit() {
    if (!promptId || !modelId) return;
    setSubmitting(true);
    setError(null);
    try {
      const run = await api.createRun({
        task_id: taskId,
        prompt_version_id: Number(promptId),
        model_config_id: Number(modelId),
        repetitions: reps,
      });
      router.push(`/runs/${run.id}`);
    } catch (e) {
      setError(String(e));
      setSubmitting(false);
    }
  }

  if (prompts.length === 0 || modelConfigs.length === 0) {
    return (
      <div className="text-xs text-slate-500">
        Crie prompts e model configs antes de rodar.
      </div>
    );
  }

  return (
    <div className="space-y-4 text-sm">
      <div className="grid gap-3 md:grid-cols-3">
        <label className="block">
          <div className="text-[11px] uppercase tracking-wide text-slate-400 mb-1">
            prompt
          </div>
          <SelectWrapper>
            <select
              value={promptId}
              onChange={(e) => setPromptId(Number(e.target.value))}
              className={selectCls}
            >
              {prompts.map((p) => (
                <option key={p.id} value={p.id}>
                  {promptOptionLabel(p)}
                </option>
              ))}
            </select>
          </SelectWrapper>
        </label>

        <label className="block">
          <div className="text-[11px] uppercase tracking-wide text-slate-400 mb-1">
            modelo
          </div>
          <SelectWrapper>
            <select
              value={modelId}
              onChange={(e) => setModelId(Number(e.target.value))}
              className={selectCls}
            >
              {modelConfigs.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.provider}/{m.model_name}
                </option>
              ))}
            </select>
          </SelectWrapper>
        </label>

        <label className="block">
          <div className="text-[11px] uppercase tracking-wide text-slate-400 mb-1">
            repetições
          </div>
          <input
            type="number"
            min={1}
            max={10}
            value={reps}
            onChange={(e) => setReps(Number(e.target.value))}
            className={inputCls}
          />
        </label>
      </div>

      <div className="flex items-center justify-between gap-4 pt-1">
        <p className="text-[11px] text-slate-400 leading-snug max-w-md">
          Cada repetição roda o dataset inteiro. Variância = desvio padrão
          entre repetições do mesmo case.
        </p>
        <Button
          variant="primary"
          size="lg"
          onClick={onSubmit}
          disabled={submitting}
        >
          {submitting ? "Enfileirando…" : "Rodar experimento →"}
        </Button>
      </div>
      {error && <div className="text-xs text-red-400">{error}</div>}
    </div>
  );
}
