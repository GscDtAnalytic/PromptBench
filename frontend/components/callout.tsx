import { cn } from "@/lib/utils";

type Tone = "info" | "warn" | "muted";

const TONE: Record<Tone, { wrap: string; bar: string; label: string }> = {
  info: {
    wrap: "border-sky-900/40 bg-sky-950/20",
    bar: "bg-sky-500/70",
    label: "text-sky-300",
  },
  warn: {
    wrap: "border-amber-900/40 bg-amber-950/20",
    bar: "bg-amber-500/70",
    label: "text-amber-300",
  },
  muted: {
    wrap: "border-slate-800 bg-slate-900/30",
    bar: "bg-slate-700",
    label: "text-slate-400",
  },
};

export function Callout({
  tone = "info",
  label,
  children,
  className,
}: {
  tone?: Tone;
  label?: string;
  children: React.ReactNode;
  className?: string;
}) {
  const t = TONE[tone];
  return (
    <div
      className={cn(
        "relative rounded-md border pl-4 pr-3 py-2.5 text-sm",
        t.wrap,
        className,
      )}
    >
      <span
        aria-hidden
        className={cn("absolute left-0 top-2 bottom-2 w-[3px] rounded-full", t.bar)}
      />
      {label && (
        <div
          className={cn(
            "text-[10px] font-semibold uppercase tracking-wider mb-0.5",
            t.label,
          )}
        >
          {label}
        </div>
      )}
      <div className="text-slate-200 leading-snug">{children}</div>
    </div>
  );
}
