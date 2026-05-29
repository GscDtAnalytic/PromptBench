import type { SliceLabel } from "./types";

/**
 * Cores por slice. Adversarial e known_failure recebem tons "quentes" para
 * sinalizar que regressões nessas faixas merecem atenção visual imediata.
 */
export const SLICE_FILL: Record<SliceLabel, string> = {
  typical: "#60a5fa", // sky-400
  edge: "#a78bfa", // violet-400
  known_failure: "#f59e0b", // amber-500
  adversarial: "#ef4444", // red-500
};

export const SLICE_LABEL_SHORT: Record<SliceLabel, string> = {
  typical: "typ",
  edge: "edge",
  known_failure: "fail",
  adversarial: "adv",
};

export const SLICE_ORDER: SliceLabel[] = [
  "typical",
  "edge",
  "known_failure",
  "adversarial",
];

export type BadgeVariant = "default" | "success" | "warning" | "danger" | "muted";

export function badgeVariantForSlice(slice: SliceLabel | null): BadgeVariant {
  if (slice === "adversarial") return "danger";
  if (slice === "known_failure") return "warning";
  if (slice === "edge") return "default";
  return "muted";
}
