import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold",
  {
    variants: {
      variant: {
        default:
          "border-slate-700 bg-slate-800 text-slate-200",
        success:
          "border-emerald-700/40 bg-emerald-900/30 text-emerald-300",
        warning:
          "border-amber-700/40 bg-amber-900/30 text-amber-300",
        danger:
          "border-red-700/40 bg-red-900/30 text-red-300",
        muted:
          "border-slate-800 bg-slate-900 text-slate-500",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant, className }))} {...props} />;
}
