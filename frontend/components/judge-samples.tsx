import { Badge } from "@/components/ui/badge";
import type { EvalResult, SliceLabel } from "@/lib/types";
import { fmtMs, fmtUSD } from "@/lib/utils";
import {
  SLICE_FILL,
  SLICE_ORDER,
  badgeVariantForSlice,
} from "@/lib/slice-style";

interface RubricSample {
  reasoning: string;
  quality: number;
  instruction_adherence: number;
  factual_structural: number;
  tone_format: number;
}

function isRubricSample(rs: Record<string, unknown> | null): boolean {
  return (
    !!rs &&
    typeof rs === "object" &&
    "reasoning" in rs &&
    "quality" in rs &&
    "instruction_adherence" in rs &&
    "factual_structural" in rs &&
    "tone_format" in rs
  );
}

function asRubric(rs: Record<string, unknown> | null): RubricSample | null {
  return isRubricSample(rs) ? (rs as unknown as RubricSample) : null;
}

function pickSamples(results: EvalResult[]): EvalResult[] {
  const bySlice = new Map<SliceLabel, EvalResult>();
  for (const r of results) {
    if (!r.slice) continue;
    const existing = bySlice.get(r.slice);
    if (!existing) {
      bySlice.set(r.slice, r);
    } else if (!asRubric(existing.rubric_scores) && asRubric(r.rubric_scores)) {
      bySlice.set(r.slice, r);
    }
  }
  return SLICE_ORDER.map((s) => bySlice.get(s)).filter(
    (r): r is EvalResult => r !== undefined,
  );
}

export function JudgeSamples({ results }: { results: EvalResult[] }) {
  const samples = pickSamples(results);
  if (samples.length === 0) return null;
  return (
    <div className="space-y-3">
      {samples.map((r) => (
        <SampleCard key={r.id} result={r} />
      ))}
    </div>
  );
}

function SampleCard({ result }: { result: EvalResult }) {
  const rub = asRubric(result.rubric_scores);
  const sliceColor = result.slice ? SLICE_FILL[result.slice] : "#475569";
  return (
    <div
      className="rounded-lg border border-slate-800 bg-slate-900/30 overflow-hidden"
      style={{ borderLeft: `3px solid ${sliceColor}` }}
    >
      {/* Cabeçalho forte */}
      <div className="flex items-center justify-between gap-3 bg-slate-900/60 px-4 py-2.5 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Badge variant={badgeVariantForSlice(result.slice)}>
            {result.slice ?? "—"}
          </Badge>
          <span className="font-mono text-xs text-slate-400">
            tc #{result.test_case_id} · rep {result.repetition_index}
          </span>
          {result.passed ? (
            <Badge variant="success">passed</Badge>
          ) : (
            <Badge variant="danger">failed</Badge>
          )}
        </div>
        <div className="text-[11px] text-slate-500 font-mono tabular-nums">
          {fmtMs(result.latency_ms)} · {fmtUSD(result.cost_usd)}
        </div>
      </div>

      <div className="grid md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-slate-800">
        {/* coluna esquerda: notas + reasoning */}
        <div className="p-4 space-y-3">
          {rub ? (
            <>
              <div className="grid grid-cols-4 gap-1.5">
                <RubricCell label="quality" v={rub.quality} />
                <RubricCell label="adherence" v={rub.instruction_adherence} />
                <RubricCell label="factual" v={rub.factual_structural} />
                <RubricCell label="tone" v={rub.tone_format} />
              </div>
              <div className="text-xs leading-relaxed">
                <div className="text-[10px] uppercase tracking-wide text-slate-500 mb-1">
                  reasoning do judge
                </div>
                <p className="text-slate-200">{rub.reasoning || "—"}</p>
              </div>
            </>
          ) : (
            <div className="text-xs text-amber-300">
              <div className="text-[10px] uppercase tracking-wide text-amber-500/70 mb-1">
                judge_error
              </div>
              {typeof result.rubric_scores === "object" &&
              result.rubric_scores &&
              "judge_error" in result.rubric_scores
                ? String(
                    (result.rubric_scores as Record<string, unknown>)
                      .judge_error,
                  )
                : "—"}
            </div>
          )}
        </div>

        {/* coluna direita: output bruto colapsável */}
        <div className="p-4">
          <details>
            <summary className="cursor-pointer text-[10px] uppercase tracking-wide text-slate-500 hover:text-slate-300">
              output bruto do modelo
            </summary>
            <pre className="mt-2 whitespace-pre-wrap break-words text-[11px] text-slate-400 font-mono leading-relaxed max-h-64 overflow-auto">
              {result.raw_output ?? "—"}
            </pre>
          </details>
        </div>
      </div>
    </div>
  );
}

function RubricCell({ label, v }: { label: string; v: number }) {
  // colore conforme a nota (vermelho=baixo, verde=alto)
  const tone =
    v <= 2
      ? "text-red-400 border-red-900/50"
      : v >= 4
        ? "text-emerald-400 border-emerald-900/50"
        : "text-slate-100 border-slate-800";
  return (
    <div className={`rounded border bg-slate-950/40 p-1.5 ${tone}`}>
      <div className="text-[9px] uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="font-mono text-sm">{v}</div>
    </div>
  );
}
