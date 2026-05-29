"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { ScoreRadar } from "@/components/score-radar";
import { SliceBreakdown } from "@/components/slice-breakdown";
import { JudgeSamples } from "@/components/judge-samples";
import { SectionHeader } from "@/components/section-header";
import { api } from "@/lib/api";
import type { EvalResult, EvalRunStatus, Scorecard } from "@/lib/types";
import { fmtMs, fmtPct, fmtRubric, fmtScore01, fmtUSD } from "@/lib/utils";

export function RunView({ runId }: { runId: number }) {
  const [status, setStatus] = useState<EvalRunStatus | null>(null);
  const [scorecard, setScorecard] = useState<Scorecard | null>(null);
  const [results, setResults] = useState<EvalResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function tick() {
      try {
        const s = await api.getRunStatus(runId);
        if (cancelled) return;
        setStatus(s);
        if (s.status === "done") {
          const [sc, rs] = await Promise.all([
            api.getScorecard(runId),
            api.listResults(runId),
          ]);
          if (!cancelled) {
            setScorecard(sc);
            setResults(rs);
          }
          return;
        }
      } catch (e) {
        if (!cancelled) setError(String(e));
        return;
      }
      setTimeout(tick, 1500);
    }
    tick();
    return () => {
      cancelled = true;
    };
  }, [runId]);

  if (error) return <div className="text-sm text-red-400">{error}</div>;
  if (!status)
    return <div className="text-sm text-slate-400">carregando...</div>;

  return (
    <div className="space-y-2">
      <header className="space-y-1.5 mb-6">
        <div className="flex items-center gap-2">
          <Link
            href="/"
            className="text-xs text-slate-500 hover:text-slate-300"
          >
            ← home
          </Link>
          <Badge
            variant={
              status.status === "done"
                ? "success"
                : status.status === "failed"
                  ? "danger"
                  : "warning"
            }
          >
            {status.status}
          </Badge>
        </div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-50">
          Run #{runId}
        </h1>
        <p className="text-sm text-slate-400">
          {status.completed}/{status.total_expected} resultados —{" "}
          {fmtPct(status.progress)}
        </p>
      </header>

      {!scorecard ? (
        <div className="rounded-md border border-slate-800 bg-slate-900/30 p-6 text-sm text-slate-400">
          Aguardando worker concluir... ({status.completed}/
          {status.total_expected})
        </div>
      ) : (
        <>
          <ScorecardView scorecard={scorecard} runId={runId} />
          {results.length > 0 && (
            <>
              <SectionHeader
                step={4}
                title="Amostras do judge"
                description="1 caso por slice. O reasoning citando evidência é parte do contrato — judge_error nunca inventa nota."
              />
              <div className="mt-4">
                <JudgeSamples results={results} />
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}

function ScorecardView({
  scorecard,
  runId,
}: {
  scorecard: Scorecard;
  runId: number;
}) {
  return (
    <div className="space-y-2">
      {/* 01 Score geral */}
      <SectionHeader
        step={1}
        title="Score geral"
        description="KPIs do run — agregação ponderada das 4 dimensões da rubrica."
      />
      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <Metric
          label="aggregate score"
          value={fmtScore01(scorecard.aggregate_score)}
          tone="primary"
          hint="média ponderada 0–1"
        />
        <Metric
          label="latência média"
          value={fmtMs(scorecard.avg_latency_ms)}
          hint="por resposta"
        />
        <Metric
          label="custo total"
          value={fmtUSD(scorecard.total_cost_usd)}
          hint="USD, do usage real"
        />
        <Metric
          label="taxa de falha"
          value={fmtPct(scorecard.failure_rate)}
          tone={scorecard.failure_rate > 0.1 ? "danger" : undefined}
          hint="checks obrigatórios"
        />
      </div>

      {/* 02 Rubrica */}
      <SectionHeader
        step={2}
        title="Rubrica (1–5)"
        description="4 dimensões avaliadas INDEPENDENTEMENTE (anti halo effect)."
      />
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-slate-800 bg-slate-900/30 p-4">
          <ScoreRadar
            quality={scorecard.quality}
            instruction_adherence={scorecard.instruction_adherence}
            factual_structural={scorecard.factual_structural}
            tone_format={scorecard.tone_format}
          />
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-900/30 p-4 grid grid-cols-2 gap-2 text-xs content-start">
          <DimValue label="quality" v={scorecard.quality} />
          <DimValue label="adherence" v={scorecard.instruction_adherence} />
          <DimValue label="factual" v={scorecard.factual_structural} />
          <DimValue label="tone" v={scorecard.tone_format} />
          <div className="col-span-2 mt-2 pt-2 border-t border-slate-800/60 text-[11px] text-slate-500 leading-snug">
            Variância: desvio padrão entre repetições do mesmo test case.{" "}
            <span className="font-mono text-slate-300">
              σ̄ = {fmtRubric(scorecard.variance)}
            </span>
          </div>
        </div>
      </div>

      {/* 03 Slices */}
      <SectionHeader
        step={3}
        title="Score por slice (0–1)"
        description="Veredito de regressão olha aqui, não na média. adversarial e known_failure estão destacados em tons quentes."
      />
      <div className="mt-4 rounded-lg border border-slate-800 bg-slate-900/30 p-4">
        <SliceBreakdown perSlice={scorecard.per_slice_breakdown} />
      </div>

      {/* Export */}
      <div className="mt-4 flex items-center gap-3 text-xs">
        <span className="text-slate-400">export:</span>
        <a
          href={api.exportUrl(runId, "csv")}
          className="rounded-md border border-slate-700 px-3 py-1.5 text-slate-200 hover:bg-slate-800"
        >
          CSV
        </a>
        <a
          href={api.exportUrl(runId, "pdf")}
          className="rounded-md border border-slate-700 px-3 py-1.5 text-slate-200 hover:bg-slate-800"
        >
          PDF
        </a>
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  tone,
  hint,
}: {
  label: string;
  value: string;
  tone?: "primary" | "danger";
  hint?: string;
}) {
  const valColor =
    tone === "danger"
      ? "text-red-400"
      : tone === "primary"
        ? "text-sky-400"
        : "text-slate-100";
  return (
    <div className="rounded-md border border-slate-800 bg-slate-900/40 p-4">
      <div className="text-[11px] uppercase tracking-wide text-slate-400">
        {label}
      </div>
      <div className={`text-2xl font-mono mt-1 ${valColor}`}>{value}</div>
      {hint && (
        <div className="text-[10px] text-slate-600 mt-1">{hint}</div>
      )}
    </div>
  );
}

function DimValue({ label, v }: { label: string; v: number }) {
  const tone =
    v <= 2
      ? "text-red-400 border-red-900/40"
      : v >= 4
        ? "text-emerald-400 border-emerald-900/40"
        : "text-slate-100 border-slate-800";
  return (
    <div className={`rounded-md border bg-slate-950/40 p-2 ${tone}`}>
      <div className="text-[11px] uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="font-mono text-lg">{fmtRubric(v)}</div>
    </div>
  );
}
