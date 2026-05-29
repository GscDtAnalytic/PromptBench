import Link from "next/link";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

/** Bloco "Atividade recente" na home — server component. */
export async function RecentActivity() {
  let runs;
  try {
    runs = await api.listRecentRuns(8);
  } catch {
    return null;
  }
  if (runs.length === 0) return null;

  return (
    <div>
      <h2 className="text-base font-semibold tracking-tight text-slate-50 mb-3">
        Atividade recente
      </h2>
      <div className="rounded-lg border border-slate-800 bg-slate-900/30 overflow-hidden">
        <table className="w-full text-xs">
          <thead className="text-slate-400 text-[11px] uppercase tracking-wide bg-slate-900/50">
            <tr>
              <th className="text-left px-3 py-2 font-medium">task</th>
              <th className="text-left px-3 py-2 font-medium">prompt</th>
              <th className="text-left px-3 py-2 font-medium">modelo</th>
              <th className="text-right px-3 py-2 font-semibold text-slate-300">
                score
              </th>
              <th className="text-left px-3 py-2 pl-4 font-semibold text-slate-300">
                status
              </th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr
                key={r.eval_run_id}
                className="group border-t border-slate-800/60 transition-colors hover:bg-slate-900/60"
              >
                <td className="px-3 py-2.5 text-slate-300">{r.task_name}</td>
                <td className="px-3 py-2.5 font-mono text-slate-200">
                  v{r.version_number}{" "}
                  <span className="text-slate-600">·</span>{" "}
                  <span className="text-slate-400">{r.prompt_version_name}</span>
                </td>
                <td className="px-3 py-2.5 text-slate-400">{r.model_name}</td>
                <td className="px-3 py-2.5 text-right font-mono font-semibold text-slate-50 tabular-nums">
                  {r.aggregate_score != null
                    ? r.aggregate_score.toFixed(3)
                    : "—"}
                </td>
                <td className="px-3 py-2.5 pl-4">
                  <Badge
                    variant={
                      r.status === "done"
                        ? "success"
                        : r.status === "failed"
                          ? "danger"
                          : r.status === "running"
                            ? "warning"
                            : "muted"
                    }
                  >
                    {r.status}
                  </Badge>
                </td>
                <td className="px-3 py-2 text-right">
                  <Link
                    href={`/runs/${r.eval_run_id}`}
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
    </div>
  );
}
