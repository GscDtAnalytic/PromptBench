import { Badge } from "@/components/ui/badge";
import type { RegressionVerdict } from "@/lib/types";
import { fmtPct, fmtRubric, fmtScore01 } from "@/lib/utils";

const NOISE_DIM = 0.05; // 1-5: deltas menores que isso ficam apagados
const NOISE_SLICE = 0.01; // 0-1: idem

export function RegressionVerdictPanel({
  verdict,
}: {
  verdict: RegressionVerdict;
}) {
  const dimFailures = verdict.dimension_deltas.filter((d) => !d.passed).length;
  const sliceFailures = verdict.slice_deltas.filter((s) => !s.passed).length;
  return (
    <div className="space-y-5">
      <VerdictHero verdict={verdict} />

      <DeltaGroup
        title="Dimensões"
        subtitle="rubrica 1–5"
        failures={dimFailures}
        total={verdict.dimension_deltas.length}
      >
        {verdict.dimension_deltas.map((d) => {
          const significant = Math.abs(d.delta) >= NOISE_DIM;
          return (
            <DeltaCard
              key={d.dimension}
              label={d.dimension}
              from={fmtRubric(d.baseline)}
              to={fmtRubric(d.candidate)}
              delta={d.delta}
              deltaText={`${d.delta >= 0 ? "+" : ""}${d.delta.toFixed(2)}`}
              passed={d.passed}
              significant={significant}
            />
          );
        })}
      </DeltaGroup>

      <DeltaGroup
        title="Slices"
        subtitle="escala 0–1, por categoria de caso"
        failures={sliceFailures}
        total={verdict.slice_deltas.length}
      >
        {verdict.slice_deltas.map((s) => {
          const significant = Math.abs(s.delta) >= NOISE_SLICE;
          return (
            <DeltaCard
              key={s.slice}
              label={s.slice}
              from={fmtScore01(s.baseline_score)}
              to={fmtScore01(s.candidate_score)}
              delta={s.delta}
              deltaText={`${s.delta >= 0 ? "+" : ""}${s.delta.toFixed(3)}`}
              passed={s.passed}
              significant={significant}
            />
          );
        })}
      </DeltaGroup>
    </div>
  );
}

function DeltaGroup({
  title,
  subtitle,
  failures,
  total,
  children,
}: {
  title: string;
  subtitle: string;
  failures: number;
  total: number;
  children: React.ReactNode;
}) {
  const passed = total - failures;
  return (
    <div>
      <div className="flex items-baseline justify-between mb-2">
        <div className="flex items-baseline gap-2">
          <h3 className="text-sm font-semibold text-slate-100">{title}</h3>
          <span className="text-[11px] text-slate-500">{subtitle}</span>
        </div>
        <div className="text-[11px] font-mono tabular-nums">
          <span className="text-emerald-400">{passed} ok</span>
          {failures > 0 && (
            <>
              <span className="text-slate-700 mx-1.5">·</span>
              <span className="text-red-400">{failures} fail</span>
            </>
          )}
        </div>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">{children}</div>
    </div>
  );
}

function DeltaCard({
  label,
  from,
  to,
  delta,
  deltaText,
  passed,
  significant,
}: {
  label: string;
  from: string;
  to: string;
  delta: number;
  deltaText: string;
  passed: boolean;
  significant: boolean;
}) {
  const tone = !significant
    ? "border-slate-800 bg-slate-900/30 opacity-60"
    : passed
      ? "border-slate-800 bg-slate-900/40 hover:border-slate-700 hover:bg-slate-900/70"
      : "border-red-700/40 bg-red-900/20 hover:border-red-600/60 hover:bg-red-900/30";
  const deltaColor = !significant
    ? "text-slate-500"
    : delta >= 0
      ? "text-emerald-400"
      : "text-red-400";
  return (
    <div
      className={`group relative rounded-md border p-2.5 text-xs transition-colors ${tone}`}
    >
      <div className="flex items-center justify-between">
        <div className="text-slate-400">{label}</div>
        {!passed && significant && (
          <span className="text-[10px] uppercase tracking-wider text-red-400 font-semibold">
            fail
          </span>
        )}
      </div>
      <div className="text-slate-100 font-mono tabular-nums mt-0.5">
        {from} <span className="text-slate-600">→</span> {to}
      </div>
      <div className={`font-mono tabular-nums ${deltaColor} mt-0.5`}>
        Δ {deltaText}
      </div>
    </div>
  );
}

function VerdictHero({ verdict }: { verdict: RegressionVerdict }) {
  if (verdict.passed) {
    return (
      <div className="rounded-lg border border-emerald-700/40 bg-emerald-950/30 p-5 flex items-start gap-4">
        <div className="flex-shrink-0 text-3xl leading-none mt-0.5" aria-hidden>
          ✓
        </div>
        <div className="flex-1 space-y-1.5">
          <div className="flex items-center gap-3">
            <Badge variant="success" className="text-sm px-3 py-1">
              APROVADO
            </Badge>
            <span className="text-xs text-slate-400">
              custo Δ {fmtPct(verdict.cost_delta_pct)}
            </span>
          </div>
          <p className="text-sm text-slate-200">
            Passou em todos os thresholds — por dimensão, por slice e custo.
            Seguro para promover.
          </p>
        </div>
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-red-700/40 bg-red-950/30 p-5 flex items-start gap-4">
      <div className="flex-shrink-0 text-3xl leading-none mt-0.5" aria-hidden>
        ✕
      </div>
      <div className="flex-1 space-y-2">
        <div className="flex items-center gap-3">
          <Badge variant="danger" className="text-sm px-3 py-1">
            REPROVADO
          </Badge>
          <span className="text-xs text-slate-400">
            custo Δ {fmtPct(verdict.cost_delta_pct)}
          </span>
        </div>
        <p className="text-sm text-slate-200">
          {verdict.failures.length === 1
            ? "1 motivo reprovou esta versão:"
            : `${verdict.failures.length} motivos reprovaram esta versão:`}
        </p>
        <ul className="list-disc list-inside text-sm text-red-200 space-y-1 ml-1">
          {verdict.failures.map((f, i) => (
            <li key={i}>{f}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
