import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function fmtUSD(n: number | null | undefined): string {
  if (n == null) return "—";
  if (n < 0.01) return `$${n.toFixed(6)}`;
  return `$${n.toFixed(4)}`;
}

export function fmtMs(n: number | null | undefined): string {
  if (n == null) return "—";
  return `${Math.round(n)}ms`;
}

export function fmtPct(n: number | null | undefined): string {
  if (n == null) return "—";
  return `${(n * 100).toFixed(1)}%`;
}

export function fmtScore01(n: number | null | undefined): string {
  if (n == null) return "—";
  return n.toFixed(3);
}

export function fmtRubric(n: number | null | undefined): string {
  if (n == null) return "—";
  return n.toFixed(2);
}
