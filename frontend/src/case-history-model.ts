import type { CaseSummary, ReviewDecision, Severity } from "./types";

/**
 * Pure client-side search/filter over an already-fetched page of cases.
 *
 * The backend's GET /api/v1/cases only supports limit/offset (see
 * docs/API_CONTRACT.md §12) -- there is no server-side query, sort, or
 * filter parameter to add one for without a backend change, which is out of
 * scope for this feature. Every field this filters on (report_id, bundle_id,
 * risk_severity, reviewer_decision) is already present on CaseSummary, so
 * filtering the page already in hand is the "simple" version the brief asks
 * for. Pure and pathless: same input always gives the same output, easy to
 * unit-test without a DOM or a mocked fetch.
 */
export function filterCases(
  cases: CaseSummary[],
  query: string,
  severity: Severity | "all",
  decision: ReviewDecision | "pending" | "all",
): CaseSummary[] {
  const q = query.trim().toLowerCase();
  return cases.filter((c) => {
    if (q && !c.report_id.toLowerCase().includes(q) && !c.bundle_id.toLowerCase().includes(q)) {
      return false;
    }
    if (severity !== "all" && c.risk_severity !== severity) {
      return false;
    }
    if (decision === "pending" && c.reviewer_decision !== null) {
      return false;
    }
    if (decision !== "all" && decision !== "pending" && c.reviewer_decision !== decision) {
      return false;
    }
    return true;
  });
}
