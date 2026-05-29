// Client tipado para a API do backend. Centraliza fetch + tratamento de erro.

import type {
  ComparisonResult,
  EvalResult,
  EvalRun,
  EvalRunStatus,
  LeaderboardEntry,
  ModelConfig,
  PromptVersion,
  RecentRunEntry,
  Rubric,
  Scorecard,
  Task,
  TestCase,
} from "./types";

// Server-side fetches (Server Components / Route Handlers) rodam dentro do
// container do frontend; precisam de hostname interno do docker. O browser usa
// o hostname público mapeado para localhost.
const BASE_URL =
  typeof window === "undefined"
    ? process.env.API_INTERNAL_URL ||
      process.env.NEXT_PUBLIC_API_BASE_URL ||
      "http://localhost:8000"
    : process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      // ignore
    }
    throw new ApiError(res.status, `${res.status}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  // Tasks
  listTasks: () => request<Task[]>("/tasks"),
  getTask: (id: number) => request<Task>(`/tasks/${id}`),
  listPrompts: (taskId: number) =>
    request<PromptVersion[]>(`/tasks/${taskId}/prompts`),
  listTestCases: (taskId: number) =>
    request<TestCase[]>(`/tasks/${taskId}/testcases`),
  getRubric: (taskId: number) => request<Rubric>(`/tasks/${taskId}/rubric`),
  getLeaderboard: (taskId: number) =>
    request<LeaderboardEntry[]>(`/tasks/${taskId}/leaderboard`),

  // Model configs
  listModelConfigs: () => request<ModelConfig[]>("/model-configs"),

  // Runs
  createRun: (body: {
    task_id: number;
    prompt_version_id: number;
    model_config_id: number;
    repetitions: number;
  }) =>
    request<EvalRun>("/runs", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listRecentRuns: (limit = 8) =>
    request<RecentRunEntry[]>(`/runs/recent?limit=${limit}`),
  getRun: (id: number) => request<EvalRun>(`/runs/${id}`),
  getRunStatus: (id: number) =>
    request<EvalRunStatus>(`/runs/${id}/status`),
  listResults: (id: number) => request<EvalResult[]>(`/runs/${id}/results`),

  // Scorecards
  getScorecard: (runId: number) =>
    request<Scorecard>(`/scorecards/${runId}`),

  // Compare
  compare: (baseline: number, candidate: number) =>
    request<ComparisonResult>(
      `/compare?baseline=${baseline}&candidate=${candidate}`,
    ),

  // Export
  exportUrl: (runId: number, format: "csv" | "pdf") =>
    `${BASE_URL}/export/${runId}?format=${format}`,
};

export { ApiError };
