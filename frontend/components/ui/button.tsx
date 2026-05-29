import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-all duration-100 focus-visible:outline-none disabled:pointer-events-none disabled:opacity-40 select-none",
  {
    variants: {
      variant: {
        default:
          "bg-slate-100 text-slate-900 hover:bg-slate-200 active:bg-slate-300 focus-visible:ring-2 focus-visible:ring-slate-300/40",
        primary:
          "bg-sky-500 text-slate-950 font-semibold shadow-sm shadow-sky-500/20 ring-1 ring-inset ring-sky-300/30 hover:bg-sky-400 hover:shadow-sky-400/30 active:bg-sky-600 active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-sky-400/60 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950",
        outline:
          "border border-slate-700 bg-transparent text-slate-200 hover:bg-slate-800 hover:border-slate-600 active:bg-slate-800/80 focus-visible:ring-2 focus-visible:ring-slate-500/40",
        ghost:
          "text-slate-300 hover:bg-slate-800 hover:text-slate-100 active:bg-slate-800/80 focus-visible:ring-2 focus-visible:ring-slate-500/40",
        destructive:
          "bg-red-600 text-white hover:bg-red-700 active:bg-red-800 focus-visible:ring-2 focus-visible:ring-red-400/60",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 px-3 text-xs",
        lg: "h-10 px-6",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  ),
);
Button.displayName = "Button";
