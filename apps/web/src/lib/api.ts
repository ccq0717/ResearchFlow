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
  search_query: string;
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

export interface ResearchTask {
  id: string;
  run_id: string;
  question_id: string;
  query: string;
  status: "pending" | "completed" | "failed";
  created_at: string;
}

export interface ResearchSource {
  id: string;
  run_id: string;
  task_id: string;
  title: string;
  url: string | null;
  snippet: string;
  retrieved_at: string;
  source_type: "academic" | "official" | "industry" | "community" | "other";
  author: string | null;
  published_at: string | null;
  publisher: string | null;
  origin: "web" | "local";
  knowledge_document_id: string | null;
  locator: string | null;
}

export interface ResearchEvidence {
  id: string;
  run_id: string;
  task_id: string;
  question_id: string;
  source_id: string;
  excerpt: string;
  summary: string;
  created_at: string;
}

export interface ResearchClaim {
  id: string;
  run_id: string;
  question_id: string;
  text: string;
  evidence_ids: string[];
  created_at: string;
}

export interface CitationAudit {
  claim_count: number;
  supported_claim_count: number;
  coverage_percent: number;
  unsupported_claim_ids: string[];
  source_type_counts: Record<ResearchSource["source_type"], number>;
}

export interface ResearchMaterials {
  run_id: string;
  tasks: ResearchTask[];
  sources: ResearchSource[];
  evidence: ResearchEvidence[];
  claims: ResearchClaim[];
  citation_audit: CitationAudit;
}

export interface KnowledgeDocument {
  id: string;
  original_filename: string;
  media_type: string;
  size_bytes: number;
  status: "processing" | "ready" | "failed";
  chunk_count: number;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!(init?.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(apiBaseUrl + path, {
    ...init,
    headers,
  });

  if (!response.ok) {
    throw new Error("请求失败（" + response.status + "）");
  }

  return response.json() as Promise<T>;
}

export function createResearchRun(
  goal: string,
  documentIds: string[] = [],
): Promise<ResearchRun> {
  return request<ResearchRun>("/api/research-runs", {
    method: "POST",
    body: JSON.stringify({ goal, document_ids: documentIds }),
  });
}

export async function listResearchRuns(): Promise<ResearchRun[]> {
  const response = await request<{ items: ResearchRun[] }>("/api/research-runs");
  return response.items;
}

export function getResearchRun(runId: string): Promise<ResearchRun> {
  return request<ResearchRun>("/api/research-runs/" + runId);
}

export function cancelResearchRun(runId: string): Promise<ResearchRun> {
  return request<ResearchRun>("/api/research-runs/" + runId + "/cancel", {
    method: "POST",
  });
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

export function getResearchMaterials(runId: string): Promise<ResearchMaterials> {
  return request<ResearchMaterials>("/api/research-runs/" + runId + "/materials");
}

export async function listKnowledgeDocuments(): Promise<KnowledgeDocument[]> {
  const response = await request<{ items: KnowledgeDocument[] }>(
    "/api/knowledge-documents",
  );
  return response.items;
}

export function uploadKnowledgeDocument(file: File): Promise<KnowledgeDocument> {
  const body = new FormData();
  body.append("file", file);
  return request<KnowledgeDocument>("/api/knowledge-documents", {
    method: "POST",
    body,
  });
}

export async function deleteKnowledgeDocument(documentId: string): Promise<void> {
  const response = await fetch(
    apiBaseUrl + "/api/knowledge-documents/" + documentId,
    { method: "DELETE" },
  );
  if (!response.ok) {
    throw new Error("删除知识文档失败（" + response.status + "）");
  }
}

export function reprocessKnowledgeDocument(
  documentId: string,
): Promise<KnowledgeDocument> {
  return request<KnowledgeDocument>(
    "/api/knowledge-documents/" + documentId + "/reprocess",
    { method: "POST" },
  );
}
