export type ResearchStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export type ResearchStage =
  | "planning"
  | "retrieving"
  | "analyzing"
  | "writing"
  | "finalizing";

export interface ResearchRun {
  id: string;
  goal: string;
  title: string;
  status: ResearchStatus;
  current_stage: ResearchStage | null;
  progress: number;
  report_markdown: string | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface ResearchQuestion {
  id: string;
  question: string;
  rationale: string;
}

export interface ResearchPlan {
  run_id: string;
  summary: string;
  questions: ResearchQuestion[];
  deliverables: string[];
  provider: string;
  model: string;
  input_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
  duration_ms: number;
  created_at: string;
}

export interface ResearchEventData {
  sequence: number;
  run_id: string;
  type: string;
  stage: ResearchStage | null;
  message: string;
  progress: number | null;
  created_at: string;
  payload: Record<string, unknown>;
}

export const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiBaseUrl + path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    throw new Error("请求失败（" + response.status + "）");
  }

  return response.json() as Promise<T>;
}

export function createResearchRun(goal: string): Promise<ResearchRun> {
  return request<ResearchRun>("/api/research-runs", {
    method: "POST",
    body: JSON.stringify({ goal }),
  });
}

export async function listResearchRuns(): Promise<ResearchRun[]> {
  const response = await request<{ items: ResearchRun[] }>("/api/research-runs");
  return response.items;
}

export function getResearchRun(runId: string): Promise<ResearchRun> {
  return request<ResearchRun>("/api/research-runs/" + runId);
}

export async function listResearchEvents(
  runId: string,
): Promise<ResearchEventData[]> {
  const response = await request<{ items: ResearchEventData[] }>(
    "/api/research-runs/" + runId + "/events/history",
  );
  return response.items;
}

export async function getResearchPlan(
  runId: string,
): Promise<ResearchPlan | null> {
  const response = await request<{ plan: ResearchPlan | null }>(
    "/api/research-runs/" + runId + "/plan",
  );
  return response.plan;
}
