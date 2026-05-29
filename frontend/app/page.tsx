import Link from "next/link";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { RecentActivity } from "@/components/recent-activity";
import { TaskCardStats } from "@/components/task-card-stats";

const TASK_TYPE_GLYPH: Record<string, string> = {
  structured_extraction: "{ }",
  classification_response: "≡",
};

export default async function HomePage() {
  let tasks;
  try {
    tasks = await api.listTasks();
  } catch (e) {
    return (
      <div className="text-sm text-slate-400">
        Não foi possível conectar ao backend ({String(e)}).
        <br />
        Subir com <code className="text-slate-200">docker compose up --build</code> e depois{" "}
        <code className="text-slate-200">make seed</code>.
      </div>
    );
  }
  return (
    <div className="space-y-10">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-50 leading-tight">
          Tasks
        </h1>
        <p className="text-sm text-slate-400 max-w-2xl leading-relaxed">
          Cada task é um conjunto <span className="text-slate-200">imutável</span>{" "}
          de versões de prompt, dataset com slices e scorecards. Use o{" "}
          <Link href="/compare" className="text-sky-400 hover:text-sky-300">
            compare
          </Link>{" "}
          para detectar regressões que a média esconde.
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        {tasks.map((t) => (
          <Link key={t.id} href={`/tasks/${t.id}`}>
            <Card className="hover:bg-slate-800/60 hover:border-slate-600 hover:shadow-md hover:shadow-slate-950/60 transition-all duration-150 h-full">
              <CardHeader>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-baseline gap-2">
                    <span className="font-mono text-slate-500 text-base">
                      {TASK_TYPE_GLYPH[t.task_type] ?? "•"}
                    </span>
                    <CardTitle className="text-base">{t.name}</CardTitle>
                  </div>
                  <Badge variant="muted">{t.task_type}</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-xs text-slate-400 leading-snug">
                  {t.description || "—"}
                </p>
                <TaskCardStats taskId={t.id} />
                <p className="text-[11px] font-mono text-slate-600">
                  /tasks/{t.slug}
                </p>
              </CardContent>
            </Card>
          </Link>
        ))}
        {tasks.length === 0 && (
          <div className="text-sm text-slate-400">
            Nenhuma task ainda. Rode <code>make seed</code>.
          </div>
        )}
      </div>

      <RecentActivity />
    </div>
  );
}
