import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ReportView } from "../components/ReportView";
import type { VerificationReport } from "../types";

/**
 * Navigation-only tests. They assert how a reader gets *back* from a report --
 * never what the report says. No analytical value is constructed or checked
 * here beyond the minimum needed to render the component.
 */

vi.mock("../api", () => ({
  getAuditTrail: vi.fn().mockResolvedValue([]),
  postDecision: vi.fn(),
}));

function makeReport(): VerificationReport {
  return {
    report_id: "rep_nav001",
    created_at: "2026-08-20T10:00:00Z",
    status: "complete",
    bundle: { bundle_id: "bnd_nav1", document_count: 1 },
    documents: [],
    consistency: {
      engine: "t", engine_version: "1", checks: [], cross_references: [],
      score: 0, summary: "none",
    },
    risk: {
      engine: "t", engine_version: "1", scope: "bundle", subject_id: "bnd_nav1",
      score: 12, severity: "low", contributions: [],
      model: { method: "m", version: "1" },
    },
    recommendation: {
      decision: "accept", confidence: 0.6, headline: "Low risk",
      reasons: [], suggested_actions: [],
      based_on: { bundle_risk_score: 12, severity: "low" },
    },
    explanation: { summary: "Nothing was flagged.", factors: [], glossary: [] },
    errors: [],
  };
}

describe("ReportView back navigation", () => {
  it("shows 'Back to case history' when the report was opened from history", async () => {
    const onBackToHistory = vi.fn();
    render(
      <ReportView report={makeReport()} onReset={vi.fn()} onBackToHistory={onBackToHistory} />,
    );

    const back = screen.getByRole("button", { name: /back to case history/i });
    await userEvent.click(back);
    expect(onBackToHistory).toHaveBeenCalledTimes(1);
  });

  it("omits the control when the report came from a fresh verification", () => {
    render(<ReportView report={makeReport()} onReset={vi.fn()} />);

    expect(screen.queryByRole("button", { name: /back to case history/i })).toBeNull();
    // The verification flow's own control is untouched.
    expect(screen.getByRole("button", { name: /new verification/i })).toBeInTheDocument();
  });

  it("reaches the control by keyboard and activates it with Enter", async () => {
    const onBackToHistory = vi.fn();
    render(
      <ReportView report={makeReport()} onReset={vi.fn()} onBackToHistory={onBackToHistory} />,
    );

    const back = screen.getByRole("button", { name: /back to case history/i });
    back.focus();
    expect(back).toHaveFocus();

    await userEvent.keyboard("{Enter}");
    expect(onBackToHistory).toHaveBeenCalledTimes(1);
  });

  it("does not disturb the report's own content", () => {
    render(
      <ReportView report={makeReport()} onReset={vi.fn()} onBackToHistory={vi.fn()} />,
    );

    // Deliberately not asserting the score digits: the gauge animates up from
    // 0, so its intermediate value is timing-dependent. The severity band and
    // the disclaimer are stable and prove the report rendered intact.
    expect(screen.getByRole("heading", { name: /low risk/i })).toBeInTheDocument();
    expect(screen.getByText(/band/i)).toBeInTheDocument();
    expect(
      screen.getByText(/prompt for human review, not a determination of fraud/i),
    ).toBeInTheDocument();
  });
});
