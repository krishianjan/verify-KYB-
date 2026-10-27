import type {
  CaseCreate,
  CaseListOut,
  CaseOut,
  FootprintOut,
  ReportOut,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      `Can't reach the API at ${API_BASE}. Is the backend running?`,
      0,
    );
  }
  if (!resp.ok) {
    let detail = `Request failed (${resp.status})`;
    try {
      const body = await resp.json();
      if (body?.detail) detail = String(body.detail);
    } catch {}
    throw new ApiError(detail, resp.status);
  }
  return (await resp.json()) as T;
}

export const createCase = (payload: CaseCreate) =>
  request<CaseOut>("/kyb/cases", { method: "POST", body: JSON.stringify(payload) });

export const getCase = (id: string) => request<CaseOut>(`/kyb/cases/${id}`);

export const getReport = (id: string) =>
  request<ReportOut>(`/kyb/cases/${id}/report`);

export const runFootprint = (id: string) =>
  request<FootprintOut>(`/kyb/cases/${id}/footprint`, { method: "POST" });

export const runEnrich = (id: string) =>
  request<FootprintOut>(`/kyb/cases/${id}/enrich`, { method: "POST" });

export const getFootprint = (id: string) =>
  request<FootprintOut>(`/kyb/cases/${id}/footprint`);

export const listCases = (params?: {
  status?: string;
  rating?: string;
  decision?: string;
  limit?: number;
}) => {
  const q = new URLSearchParams();
  if (params?.status) q.set("status", params.status);
  if (params?.rating) q.set("rating", params.rating);
  if (params?.decision) q.set("decision", params.decision);
  if (params?.limit) q.set("limit", String(params.limit));
  const qs = q.toString();
  return request<CaseListOut>(`/kyb/cases${qs ? `?${qs}` : ""}`);
};

export const postAction = (
  id: string,
  action: "approve" | "reject" | "request_docs" | "escalate",
  notes?: string,
  actor = "analyst",
) =>
  request<{ status: string; action: string }>(`/kyb/cases/${id}/actions`, {
    method: "POST",
    body: JSON.stringify({ action, notes, actor }),
  });
