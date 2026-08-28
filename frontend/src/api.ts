// Thin client for the EvidenceGuard backend.
// In dev, VITE_API_BASE_URL is empty and Vite proxies "/health" + "/api/*"
// to the backend (see vite.config.ts). In other environments, set
// VITE_API_BASE_URL to the backend origin.

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
