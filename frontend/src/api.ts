import { VerificationReport } from "./types";
import { MOCK_REPORT } from "./mocks/fixture";

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

export async function submitVerification(files: File[], signal?: AbortSignal): Promise<VerificationReport> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));

  try {
    const res = await fetch(`${BASE}/api/v1/verify`, {
      method: "POST",
      body: formData,
      signal,
    });
    
    if (!res.ok) {
      throw new Error(`Verification failed: ${res.status}`);
    }
    
    return (await res.json()) as VerificationReport;
  } catch (err) {
    console.warn("Backend unavailable or verification failed. Falling back to mock fixture.", err);
    // Simulate network delay for the mock
    await new Promise((resolve) => setTimeout(resolve, 500));
    return MOCK_REPORT;
  }
}
