// Tipos espelhados do backend (FastAPI). Mantidos manualmente — o openapi pode ser
// usado pra gerar isso depois, mas aqui mantém-se simples e claro.

export type TaskType = "structured_extraction" | "classification_response";
export type SliceLabel = "typical" | "edge" | "known_failure" | "adversarial";
export type Provider = "fake" | "claude" | "openai" | "gemini";
export type RunStatus = "pending" | "running" | "done" | "failed";

export interface Task {
  id: number;
  name: string;
  slug: string;
  description: string;
  task_type: TaskType;
  created_at: string;
}

export interface PromptVersion {
  id: number;
  task_id: number;
  version_number: number;
  name: string;
  system_prompt: string;
  user_template: string;
  model_params: Record<string, unknown>;
  is_baseline: boolean;
  created_at: string;
}

export interface TestCase {
  id: number;
  task_id: number;
  input: Record<string, unknown>;
  expected: Record<string, unknown> | null;
  slice: SliceLabel;
  rubric_notes: string | null;
}

export interface ModelConfig {
  id: number;
  provider: Provider;
  model_name: string;
  temperature: number;
  max_tokens: number;
  price_per_1m_input: number;
  price_per_1m_output: number;
}

export interface EvalRun {
  id: number;
  task_id: number;
  prompt_version_id: number;
  model_config_id: number;
  status: RunStatus;
  repetitions: number;
  created_at: string;
  finished_at: string | null;
}

export interface EvalRunStatus {
  id: number;
  status: RunStatus;
  total_expected: number;
  completed: number;
  progress: number;
}

export interface EvalResult {
  id: number;
  eval_run_id: number;
  test_case_id: number;
  repetition_index: number;
  raw_output: string | null;
  latency_ms: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
  cost_usd: number | null;
  deterministic_scores: Record<string, { passed: boolean; score: number; detail: string }> | null;
  rubric_scores: Record<string, unknown> | null;
  passed: boolean;
  error: string | null;
  slice: SliceLabel | null;
}

export interface SliceMetrics {
  aggregate_score: number;
  quality: number;
  instruction_adherence: number;
  factual_structural: number;
  tone_format: number;
  failure_rate: number;
  count: number;
}

export interface Scorecard {
  id: number;
  eval_run_id: number;
  aggregate_score: number;
  quality: number;
  instruction_adherence: number;
  factual_structural: number;
  tone_format: number;
  avg_latency_ms: number;
  total_cost_usd: number;
  failure_rate: number;
  variance: number;
  per_slice_breakdown: Record<string, SliceMetrics>;
}

export interface LeaderboardEntry {
  eval_run_id: number;
  prompt_version_id: number;
  prompt_version_name: string;
  version_number: number;
  model_config_id: number;
  model_name: string;
  aggregate_score: number;
  avg_latency_ms: number;
  total_cost_usd: number;
  failure_rate: number;
}

export interface DimensionDelta {
  dimension: string;
  baseline: number;
  candidate: number;
  delta: number;
  passed: boolean;
}

export interface SliceDelta {
  slice: string;
  baseline_score: number;
  candidate_score: number;
  delta: number;
  passed: boolean;
}

export interface RegressionVerdict {
  passed: boolean;
  failures: string[];
  dimension_deltas: DimensionDelta[];
  slice_deltas: SliceDelta[];
  cost_delta_pct: number;
  cost_passed: boolean;
}

export interface ComparisonResult {
  baseline_run_id: number;
  candidate_run_id: number;
  verdict: RegressionVerdict;
}

export interface Rubric {
  task_description: string;
  rubric_criteria: string;
  dimensions: string[];
  weights: Record<string, number>;
  anchors: string;
}

export interface RecentRunEntry {
  eval_run_id: number;
  task_id: number;
  task_slug: string;
  task_name: string;
  prompt_version_name: string;
  version_number: number;
  model_name: string;
  status: RunStatus;
  aggregate_score: number | null;
  created_at: string;
}
