import { cn } from "@/lib/utils";

interface Props {
  step?: number;
  title: string;
  description?: string;
  className?: string;
}

/**
 * Cabeçalho de seção numerada — usado para guiar a leitura em telas longas
 * sem precisar de nav lateral. Border-top opcional para separação visual.
 */
export function SectionHeader({ step, title, description, className }: Props) {
  return (
    <div className={cn("border-t border-slate-800 pt-7 mt-2", className)}>
      <div className="flex items-baseline gap-3">
        {step !== undefined && (
          <span className="text-xs font-mono text-slate-600 tabular-nums">
            {String(step).padStart(2, "0")}
          </span>
        )}
        <h2 className="text-base font-semibold tracking-tight text-slate-50">
          {title}
        </h2>
      </div>
      {description && (
        <p className="mt-1.5 text-xs text-slate-400 leading-snug ml-7 first:ml-0">
          {description}
        </p>
      )}
    </div>
  );
}
