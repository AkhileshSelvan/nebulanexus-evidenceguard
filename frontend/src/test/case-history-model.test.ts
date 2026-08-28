import { describe, it, expect } from "vitest";
import { filterCases } from "../case-history-model";
import type { CaseSummary } from "../types";

function makeCase(overrides: Partial<CaseSummary> = {}): CaseSummary {
  return {
    report_id: "rep_aaaa0001",
    bundle_id: "bnd_bbbb0001",
    created_at: "2026-08-01T10:00:00Z",
    status: "complete",
    document_count: 2,
    risk_score: 10,
    risk_severity: "low",
    recommendation_decision: "accept",
    reviewer_decision: null,
    reviewer_name: null,
    reviewer_notes: null,
    reviewed_at: null,
    ...overrides,
  };
}

describe("filterCases", () => {
  const cases: CaseSummary[] = [
    makeCase({ report_id: "rep_alpha001", bundle_id: "bnd_x1", risk_severity: "low", reviewer_decision: null }),
    makeCase({ report_id: "rep_beta002", bundle_id: "bnd_x2", risk_severity: "high", reviewer_decision: "reject" }),
    makeCase({ report_id: "rep_gamma003", bundle_id: "bnd_x3", risk_severity: "medium", reviewer_decision: "accept" }),
    makeCase({ report_id: "rep_delta004", bundle_id: "bnd_x4", risk_severity: "critical", reviewer_decision: "review" }),
  ];

  it("returns everything when there is no query or filter", () => {
    expect(filterCases(cases, "", "all", "all")).toHaveLength(4);
  });

  it("matches search text against report_id, case-insensitively", () => {
    const result = filterCases(cases, "ALPHA", "all", "all");
    expect(result.map((c) => c.report_id)).toEqual(["rep_alpha001"]);
  });

  it("matches search text against bundle_id too", () => {
    const result = filterCases(cases, "bnd_x3", "all", "all");
    expect(result.map((c) => c.report_id)).toEqual(["rep_gamma003"]);
  });

  it("filters by severity", () => {
    const result = filterCases(cases, "", "high", "all");
    expect(result.map((c) => c.report_id)).toEqual(["rep_beta002"]);
  });

  it("filters by an explicit decision", () => {
    const result = filterCases(cases, "", "all", "accept");
    expect(result.map((c) => c.report_id)).toEqual(["rep_gamma003"]);
  });

  it("filters by pending (null) reviewer decision", () => {
    const result = filterCases(cases, "", "all", "pending");
    expect(result.map((c) => c.report_id)).toEqual(["rep_alpha001"]);
  });

  it("combines search and filter (AND semantics)", () => {
    const result = filterCases(cases, "rep_", "critical", "review");
    expect(result.map((c) => c.report_id)).toEqual(["rep_delta004"]);
  });

  it("returns an empty array when nothing matches", () => {
    expect(filterCases(cases, "no-such-case", "all", "all")).toEqual([]);
  });

  it("never mutates the input array", () => {
    const copy = [...cases];
    filterCases(cases, "beta", "all", "all");
    expect(cases).toEqual(copy);
  });
});
