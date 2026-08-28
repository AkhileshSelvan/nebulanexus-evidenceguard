import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DecisionHistory } from "../components/DecisionHistory";
import type { AuditEvent, CaseSummary } from "../types";

const { listCasesMock, getAuditTrailMock } = vi.hoisted(() => ({
  listCasesMock: vi.fn(),
  getAuditTrailMock: vi.fn(),
}));
vi.mock("../api", () => ({
  listCases: listCasesMock,
  getAuditTrail: getAuditTrailMock,
}));

function makeCase(overrides: Partial<CaseSummary> = {}): CaseSummary {
  return {
    report_id: "rep_alpha001",
    bundle_id: "bnd_x1",
    created_at: "2026-08-20T10:00:00Z",
    status: "complete",
    document_count: 2,
    risk_score: 34,
    risk_severity: "medium",
    recommendation_decision: "review",
    reviewer_decision: "review",
    reviewer_name: "Priya R",
    reviewer_notes: null,
    reviewed_at: "2026-08-21T09:00:00Z",
    ...overrides,
  };
}

function makeEvent(overrides: Partial<AuditEvent> = {}): AuditEvent {
  return {
    id: "aud_0001",
    report_id: "rep_alpha001",
    event_type: "decision_recorded",
    actor: "Priya R",
    detail: { decision: "review", notes: null },
    at: "2026-08-21T09:00:00Z",
    ...overrides,
  };
}

describe("DecisionHistory", () => {
  beforeEach(() => {
    listCasesMock.mockReset();
    getAuditTrailMock.mockReset();
  });

  it("shows matching cases as the user searches", async () => {
    const user = userEvent.setup();
    listCasesMock.mockResolvedValue([
      makeCase({ report_id: "rep_alpha001" }),
      makeCase({ report_id: "rep_beta002", bundle_id: "bnd_x2" }),
    ]);
    render(<DecisionHistory />);

    const input = await screen.findByLabelText(/^case$/i);
    await user.type(input, "alpha");

    expect(await screen.findByText("rep_alpha001")).toBeInTheDocument();
    expect(screen.queryByText("rep_beta002")).not.toBeInTheDocument();
  });

  it("shows a no-matches message for a search with no results", async () => {
    const user = userEvent.setup();
    listCasesMock.mockResolvedValue([makeCase()]);
    render(<DecisionHistory />);

    await user.type(await screen.findByLabelText(/^case$/i), "nonexistent");

    expect(await screen.findByText(/no cases match/i)).toBeInTheDocument();
  });

  it("loads and displays every decision event for the selected case, oldest first as returned", async () => {
    const user = userEvent.setup();
    listCasesMock.mockResolvedValue([makeCase()]);
    getAuditTrailMock.mockResolvedValue([
      makeEvent({ id: "aud_0001", event_type: "report_created", actor: null, detail: {}, at: "2026-08-20T10:00:00Z" }),
      makeEvent({ id: "aud_0002", detail: { decision: "review", notes: "Needs a second pass." }, at: "2026-08-20T11:00:00Z" }),
      makeEvent({ id: "aud_0003", actor: "Akhilesh", detail: { decision: "reject", notes: null }, at: "2026-08-21T09:00:00Z" }),
    ]);
    render(<DecisionHistory />);

    await user.type(await screen.findByLabelText(/^case$/i), "alpha");
    await user.click(await screen.findByText("rep_alpha001"));

    expect(await screen.findByText("Flagged for review")).toBeInTheDocument();
    expect(screen.getByText("Rejected")).toBeInTheDocument();
    expect(screen.getByText(/needs a second pass/i)).toBeInTheDocument();
    expect(screen.getByText(/by akhilesh/i)).toBeInTheDocument();
  });

  it("excludes report_created events from the decision list and count", async () => {
    const user = userEvent.setup();
    listCasesMock.mockResolvedValue([makeCase()]);
    getAuditTrailMock.mockResolvedValue([
      makeEvent({ id: "aud_0001", event_type: "report_created", actor: null, detail: {}, at: "2026-08-20T10:00:00Z" }),
      makeEvent({ id: "aud_0002" }),
    ]);
    render(<DecisionHistory />);

    await user.type(await screen.findByLabelText(/^case$/i), "alpha");
    await user.click(await screen.findByText("rep_alpha001"));

    expect(await screen.findByText("1 decision recorded")).toBeInTheDocument();
  });

  it("shows the full count when a case has more than one decision on record", async () => {
    const user = userEvent.setup();
    listCasesMock.mockResolvedValue([makeCase()]);
    getAuditTrailMock.mockResolvedValue([
      makeEvent({ id: "aud_0002" }),
      makeEvent({ id: "aud_0003", detail: { decision: "reject", notes: null } }),
    ]);
    render(<DecisionHistory />);

    await user.type(await screen.findByLabelText(/^case$/i), "alpha");
    await user.click(await screen.findByText("rep_alpha001"));

    expect(await screen.findByText("2 decisions recorded")).toBeInTheDocument();
  });

  it("shows an empty message when a case has no decisions recorded yet", async () => {
    const user = userEvent.setup();
    listCasesMock.mockResolvedValue([makeCase()]);
    getAuditTrailMock.mockResolvedValue([
      makeEvent({ id: "aud_0001", event_type: "report_created", actor: null, detail: {}, at: "2026-08-20T10:00:00Z" }),
    ]);
    render(<DecisionHistory />);

    await user.type(await screen.findByLabelText(/^case$/i), "alpha");
    await user.click(await screen.findByText("rep_alpha001"));

    expect(await screen.findByText(/no decisions have been recorded/i)).toBeInTheDocument();
  });

  it("shows an honest error, never a fabricated case list, when loading cases fails", async () => {
    listCasesMock.mockRejectedValue(new Error("List cases failed: backend responded 500"));
    render(<DecisionHistory />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/backend responded 500/i);
  });

  it("shows an honest error, never fabricated decisions, when loading the audit trail fails", async () => {
    const user = userEvent.setup();
    listCasesMock.mockResolvedValue([makeCase()]);
    getAuditTrailMock.mockRejectedValue(new Error("Get audit trail failed: backend responded 404"));
    render(<DecisionHistory />);

    await user.type(await screen.findByLabelText(/^case$/i), "alpha");
    await user.click(await screen.findByText("rep_alpha001"));

    const alerts = await screen.findAllByRole("alert");
    expect(alerts.some((a) => /backend responded 404/i.test(a.textContent ?? ""))).toBe(true);
  });

  it("calls onBack when the back link is clicked", async () => {
    const user = userEvent.setup();
    const onBack = vi.fn();
    listCasesMock.mockResolvedValue([]);
    render(<DecisionHistory onBack={onBack} />);

    await user.click(await screen.findByRole("button", { name: /back/i }));
    expect(onBack).toHaveBeenCalledTimes(1);
  });

  it("renders no back link when onBack is not provided", async () => {
    listCasesMock.mockResolvedValue([]);
    render(<DecisionHistory />);

    await screen.findByLabelText(/^case$/i);
    expect(screen.queryByRole("button", { name: /back/i })).not.toBeInTheDocument();
  });

  it("scopes the decision timeline to only the selected case's events", async () => {
    const user = userEvent.setup();
    listCasesMock.mockResolvedValue([makeCase()]);
    getAuditTrailMock.mockResolvedValue([makeEvent()]);
    render(<DecisionHistory />);

    await user.type(await screen.findByLabelText(/^case$/i), "alpha");
    await user.click(await screen.findByText("rep_alpha001"));

    await screen.findByText("Flagged for review");
    expect(getAuditTrailMock).toHaveBeenCalledWith("rep_alpha001", expect.anything());
    expect(within(screen.getByRole("list")).getAllByRole("listitem")).toHaveLength(1);
  });
});
