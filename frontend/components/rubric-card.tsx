import { Badge } from "@/components/ui/badge";
import type { Rubric } from "@/lib/types";

const ANCHOR_META: Record<string, { label: string; border: string; title: string; dot: string }> = {
  BOM: {
    label: "BOM",
    border: "border-emerald-800/60 bg-emerald-950/30",
    title: "text-emerald-400",
    dot: "bg-emerald-500",
  },
  MÉDIO: {
    label: "MÉDIO",
    border: "border-amber-800/60 bg-amber-950/20",
    title: "text-amber-400",
    dot: "bg-amber-500",
  },
  RUIM: {
    label: "RUIM",
    border: "border-red-900/60 bg-red-950/20",
    title: "text-red-400",
    dot: "bg-red-500",
  },
};

function parseAnchors(text: string) {
  const blocks = text.split(/(?=Anchor (?:BOM|MÉDIO|RUIM))/).filter((b) => b.trim());
  return blocks.map((block) => {
    const header = block.match(/^Anchor (BOM|MÉDIO|RUIM)[^\n]*/)?.[0] ?? "";
    const level = block.match(/^Anchor (BOM|MÉDIO|RUIM)/)?.[1] ?? "";
    const body = block.slice(header.length).trim();
    const lines = body.split("\n").map((l) => l.replace(/^\s+/, ""));
    const output = lines.find((l) => l.startsWith("Output:"))?.replace("Output:", "").trim() ?? "";
    const notas = lines.find((l) => l.startsWith("Notas:"))?.replace("Notas:", "").trim() ?? "";
    const razao = lines.find((l) => l.startsWith("Razão:"))?.replace("Razão:", "").trim() ?? "";
    return { level, header, output, notas, razao };
  });
}

function AnchorCards({ anchors }: { anchors: string }) {
  const blocks = parseAnchors(anchors);
  if (!blocks.length) {
    return (
      <pre className="whitespace-pre-wrap text-[11px] text-slate-300 font-mono leading-relaxed">
        {anchors}
      </pre>
    );
  }
  return (
    <div className="grid gap-2 sm:grid-cols-3">
      {blocks.map(({ level, output, notas, razao }) => {
        const meta = ANCHOR_META[level] ?? ANCHOR_META["BOM"];
        return (
          <div
            key={level}
            className={`rounded-md border p-2.5 space-y-1.5 ${meta.border}`}
          >
            <div className="flex items-center gap-1.5">
              <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${meta.dot}`} />
              <span className={`text-[10px] font-bold uppercase tracking-widest ${meta.title}`}>
                {level}
              </span>
            </div>
            {output && (
              <div>
                <div className="text-[9px] uppercase text-slate-500 mb-0.5">output</div>
                <code className="text-[10px] text-slate-300 font-mono leading-snug break-all">
                  {output}
                </code>
              </div>
            )}
            {notas && (
              <div>
                <div className="text-[9px] uppercase text-slate-500 mb-0.5">notas</div>
                <span className="text-[10px] text-slate-200 font-mono">{notas}</span>
              </div>
            )}
            {razao && (
              <div>
                <div className="text-[9px] uppercase text-slate-500 mb-0.5">razão</div>
                <p className="text-[10px] text-slate-300 leading-snug">{razao}</p>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

const SHORT_BY_DIM: Record<string, string> = {
  quality: "clareza geral e relevância da resposta",
  instruction_adherence: "segue formato JSON e campos pedidos",
  factual_structural: "sem alucinar; valores plausíveis",
  tone_format: "tom adequado; respeita política",
};

export function RubricCard({ rubric }: { rubric: Rubric }) {
  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-400 leading-snug">
        4 dimensões avaliadas{" "}
        <span className="text-slate-200">independentemente</span>, notas 1–5,
        âncoras calibradas.
      </p>

      <div className="overflow-hidden rounded-md border border-slate-800">
        <table className="w-full text-xs">
          <thead className="bg-slate-900/60 text-slate-400 text-[11px] uppercase tracking-wide">
            <tr>
              <th className="text-left px-3 py-2">dimensão</th>
              <th className="text-right px-3 py-2">peso</th>
              <th className="text-left px-3 py-2">o que mede</th>
            </tr>
          </thead>
          <tbody>
            {rubric.dimensions.map((dim) => (
              <tr key={dim} className="border-t border-slate-800/70">
                <td className="px-3 py-2 font-mono text-slate-200">{dim}</td>
                <td className="px-3 py-2 text-right font-mono text-slate-100 tabular-nums">
                  {rubric.weights[dim]?.toFixed(2) ?? "—"}
                </td>
                <td className="px-3 py-2 text-slate-300">
                  {SHORT_BY_DIM[dim] ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="muted">temperature 0.0</Badge>
        <Badge variant="muted">1 retry em parse-error</Badge>
        <Badge variant="muted">judge_error nunca inventa nota</Badge>
      </div>

      <details className="rounded-md border border-slate-800 bg-slate-900/30 text-xs group">
        <summary className="cursor-pointer px-3 py-2.5 text-slate-300 font-medium hover:text-slate-100 select-none flex items-center gap-2">
          <span className="text-slate-500 text-[10px] group-open:rotate-90 transition-transform inline-block">▶</span>
          Contrato completo — descrição, critérios e âncoras de calibração
        </summary>

        <div className="border-t border-slate-800 divide-y divide-slate-800/60">
          {/* Descrição da task */}
          <div className="px-3 py-3">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-1 h-3 rounded-full bg-sky-500/70 inline-block shrink-0" />
              <span className="uppercase tracking-wider text-[10px] font-semibold text-sky-400/80">
                Descrição da task (input do judge)
              </span>
            </div>
            <p className="text-slate-200 leading-relaxed pl-3">
              {rubric.task_description}
            </p>
          </div>

          {/* Critérios da rubrica */}
          <div className="px-3 py-3">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-1 h-3 rounded-full bg-violet-500/70 inline-block shrink-0" />
              <span className="uppercase tracking-wider text-[10px] font-semibold text-violet-400/80">
                Critérios da rubrica
              </span>
            </div>
            <p className="text-slate-200 leading-relaxed whitespace-pre-line pl-3">
              {rubric.rubric_criteria}
            </p>
          </div>

          {/* Âncoras many-shot */}
          <div className="px-3 py-3">
            <div className="flex items-center gap-2 mb-3">
              <span className="w-1 h-3 rounded-full bg-amber-500/70 inline-block shrink-0" />
              <span className="uppercase tracking-wider text-[10px] font-semibold text-amber-400/80">
                Âncoras many-shot — calibração 1–5
              </span>
            </div>
            <AnchorCards anchors={rubric.anchors} />
          </div>
        </div>
      </details>
    </div>
  );
}
