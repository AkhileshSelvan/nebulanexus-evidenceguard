import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { listCases, getCase } from "../api";
import type { CaseSummary } from "../types";

function sampleCase(overrides: Partial<CaseSummary> = {}): CaseSummary {
  return {
    report_id: "rep_7f3c1a92",
    bundle_id: "bnd_1a2b3c",
    created_at: "2026-08-28T10:36:00Z",
    status: "complete",
    document_count: 3,
    risk_score: 0,
    risk_severity: "low",
    recommendation_decision: "accept",
    reviewer_decision: null,
    reviewer_name: null,
    reviewer_notes: null,
    reviewed_at: null,
    ...overrides,
  };
}

describe("listCases", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("calls GET /api/v1/cases with no query string when no options are given", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ cases: [sampleCase()] }),
    });

    const result = await listCases();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/cases");
    expect(result).toHaveLength(1);
    expect(result[0].report_id).toBe("rep_7f3c1a92");
  });

  it("encodes limit and offset as query parameters", async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ cases: [] }) });

    await listCases({ limit: 25, offset: 50 });

    const [url] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/cases?limit=25&offset=50");
  });

  it("returns the cases array from the response body, unwrapped", async () => {
    const cases = [sampleCase({ report_id: "rep_a" }), sampleCase({ report_id: "rep_b" })];
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ cases }) });

    const result = await listCases();

    expect(result.map((c) => c.report_id)).toEqual(["rep_a", "rep_b"]);
  });

  it("throws with the status code when the backend responds with an error", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500, json: async () => ({}) });

    await expect(listCases()).rejects.toThrow(/500/);
  });

  it("never fabricates a case list when the request fails outright", async () => {
    fetchMock.mockRejectedValue(new Error("network down"));

    await expect(listCases()).rejects.toThrow("network down");
  });
});

describe("getCase", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("URL-encodes the report id into the path", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({
        report: {},
        reviewer_decision: null,
        reviewer_name: null,
        reviewer_notes: null,
        reviewed_at: null,
      }),
    });

    await getCase("rep with spaces");

    const [url] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/cases/rep%20with%20spaces");
  });

  it("throws on a 404 rather than returning an empty/fabricated case", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 404, json: async () => ({}) });

    await expect(getCase("rep_missing")).rejects.toThrow(/404/);
  });
});
