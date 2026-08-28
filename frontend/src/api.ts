// Thin client for the EvidenceGuard backend.
// In dev, VITE_API_BASE_URL is empty and Vite proxies "/health" + "/api/*"
// to the backend (see vite.config.ts). In other environments, set
// VITE_API_BASE_URL to the backend origin.
//
// Response shapes live in ./types.ts (the TS mirror of docs/API_CONTRACT.md)
// — this file is only fetch plumbing, no shape definitions of its own.

import type {
  AuditEvent,
  CaseDetail,
  CaseSummary,
  DecisionRequest,
  DecisionResult,
  VerificationReport,
} from "./types";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  time: string;
}

export type BackendStatus =
  | { state: "checking" }
  | { state: "online"; health: HealthResponse }
  | { state: "offline"; error: string };

export async function checkHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const res = await fetch(`${BASE}/health`, { signal });
  if (!res.ok) {
    throw new Error(`Backend responded ${res.status}`);
  }
  return (await res.json()) as HealthResponse;
}

async function asJsonOrThrow<T>(res: Response, action: string): Promise<T> {
  if (!res.ok) {
    // The backend returns a plain-text/HTML error body on 4xx/5xx, not JSON
    // shaped like a contract type — surface the status rather than trying
    // (and failing) to parse it as one.
    throw new Error(`${action} failed: backend responded ${res.status}`);
  }
  return (await res.json()) as T;
}

/**
 * POST /api/v1/verify — the real, non-stubbed pipeline (real OCR, forensics,
 * consistency, risk fusion). `declaredTypes[i]` is an optional hint for
 * `files[i]`; pass `undefined` for a file with no hint.
 */
export async function verifyBundle(
  files: File[],
  declaredTypes?: (string | undefined)[],
  signal?: AbortSignal,
): Promise<VerificationReport> {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  (declaredTypes ?? []).forEach((t) => {
    if (t) form.append("declared_types", t);
  });
  const res = await fetch(`${BASE}/api/v1/verify`, { method: "POST", body: form, signal });
  return asJsonOrThrow<VerificationReport>(res, "Verify");
}

/** GET /api/v1/cases — newest first. */
export async function listCases(
  opts: { limit?: number; offset?: number } = {},
  signal?: AbortSignal,
): Promise<CaseSummary[]> {
  const params = new URLSearchParams();
  if (opts.limit != null) params.set("limit", String(opts.limit));
  if (opts.offset != null) params.set("offset", String(opts.offset));
  const qs = params.toString();
  const res = await fetch(`${BASE}/api/v1/cases${qs ? `?${qs}` : ""}`, { signal });
  const body = await asJsonOrThrow<{ cases: CaseSummary[] }>(res, "List cases");
  return body.cases;
}

/** GET /api/v1/cases/{report_id} — the full report plus reviewer state. */
export async function getCase(reportId: string, signal?: AbortSignal): Promise<CaseDetail> {
  const res = await fetch(`${BASE}/api/v1/cases/${encodeURIComponent(reportId)}`, { signal });
  return asJsonOrThrow<CaseDetail>(res, "Get case");
}

/**
 * POST /api/v1/cases/{report_id}/decision — records (or overwrites) the
 * case's current reviewer decision. The prior decision is never lost: every
 * post is appended to the audit trail, retrievable via getAuditTrail().
 */
export async function postDecision(
  reportId: string,
  decision: DecisionRequest,
  signal?: AbortSignal,
): Promise<DecisionResult> {
  const res = await fetch(`${BASE}/api/v1/cases/${encodeURIComponent(reportId)}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(decision),
    signal,
  });
  return asJsonOrThrow<DecisionResult>(res, "Submit decision");
}

/** GET /api/v1/cases/{report_id}/audit — full trail, oldest first. */
export async function getAuditTrail(reportId: string, signal?: AbortSignal): Promise<AuditEvent[]> {
  const res = await fetch(`${BASE}/api/v1/cases/${encodeURIComponent(reportId)}/audit`, { signal });
  const body = await asJsonOrThrow<{ report_id: string; events: AuditEvent[] }>(res, "Get audit trail");
  return body.events;
}

