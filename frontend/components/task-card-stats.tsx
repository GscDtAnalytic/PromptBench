import { api } from "@/lib/api";

interface Props {
  taskId: number;
}

/** Server component: busca counts em paralelo e mostra "5 versões · 30 casos · N runs". */
export async function TaskCardStats({ taskId }: Props) {
  const [prompts, testcases, leaderboard] = await Promise.all([
    api.listPrompts(taskId).catch(() => []),
    api.listTestCases(taskId).catch(() => []),
    api.getLeaderboard(taskId).catch(() => []),
  ]);
  const slices = testcases.reduce<Record<string, number>>((acc, tc) => {
    acc[tc.slice] = (acc[tc.slice] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-2">
      <div className="text-xs text-slate-400 font-mono">
        {prompts.length} versões · {testcases.length} casos ·{" "}
        {leaderboard.length} runs
      </div>
      <div className="flex flex-wrap gap-1.5 text-[11px]">
        {Object.entries(slices)
          .sort()
          .map(([s, n]) => (
            <span
              key={s}
              className="rounded border border-slate-800 bg-slate-900/50 px-1.5 py-0.5 text-slate-400"
            >
              {s}: {n}
            </span>
          ))}
      </div>
    </div>
  );
}
