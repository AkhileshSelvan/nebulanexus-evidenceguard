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

/**
 * The exact trail the real backend returns for a case that was flagged for
 * review, then rejected, then accepted -- captured from a live
 * GET /api/v1/cases/{report_id}/audit run against app.main.
 *
 * Two properties of the real endpoint this fixture preserves:
 *  - `report_created` always leads the trail and is NOT a decision.
 *  - Decisions come back oldest-first. The backend orders by `rowid`, not by
 *    `at` (see backend/app/audit.py::list_for_case), because `at` is only
 *    second-precision -- in a real run all four events can share one
 *    timestamp, so insertion order is the only reliable ordering.
 */
const REALISTIC_TRAIL: AuditEvent[] = [
  makeEvent({
    id: "aud_b09223e32dd0",
    event_type: "report_created",
    actor: null,
    detail: { document_count: 1, status: "complete" },
    at: "2026-08-20T10:00:00Z",
  }),
  makeEvent({
    id: "aud_23a565d2b959",
    actor: "Priya R",
    detail: { decision: "review", notes: "Needs a second pass." },
    at: "2026-08-20T11:00:00Z",
  }),
  makeEvent({
    id: "aud_dae3872110df",
    actor: "Akhilesh",
    detail: { decision: "reject", notes: "Tampering indicators on page 2." },
    at: "2026-08-21T09:00:00Z",
  }),
  makeEvent({
    id: "aud_c79c7910986d",
    actor: "Agalya",
    detail: { decision: "accept", notes: "Cleared after re-scan." },
    at: "2026-08-22T14:30:00Z",
  }),
];

/** Search for and open the one case the mocks return. */
async function openCase(user: ReturnType<typeof userEvent.setup>) {
  await user.type(await screen.findByLabelText(/^case$/i), "alpha");
  await user.click(await screen.findByText("rep_alpha001"));
}

/** The rendered decision timeline, in DOM order. */
function timelineItems(): HTMLElement[] {
  return within(screen.getByRole("list")).getAllByRole("listitem");
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

  it("renders all three decisions of a review -> reject -> accept trail", async () => {
    const user = userEvent.setup();
    listCasesMock.mockResolvedValue([makeCase()]);
    getAuditTrailMock.mockResolvedValue(REALISTIC_TRAIL);
    render(<DecisionHistory />);
    await openCase(user);

    expect(await screen.findByText("Flagged for review")).toBeInTheDocument();
    expect(screen.getByText("Rejected")).toBeInTheDocument();
    expect(screen.getByText("Accepted")).toBeInTheDocument();
    expect(screen.getByText("3 decisions recorded")).toBeInTheDocument();
  });

  it("does not render report_created as a decision in a full trail", async () => {
    const user = userEvent.setup();
    listCasesMock.mockResolvedValue([makeCase()]);
    getAuditTrailMock.mockResolvedValue(REALISTIC_TRAIL);
    render(<DecisionHistory />);
    await openCase(user);

    await screen.findByText("Flagged for review");
    // Four audit events in, three decisions out: the creation event is filtered.
    expect(timelineItems()).toHaveLength(3);
    expect(screen.queryByText(/report created/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/decision recorded/i)).not.toBeInTheDocument();
  });

  it("orders the decisions oldest-first, exactly as the audit endpoint returns them", async () => {
    const user = userEvent.setup();
    listCasesMock.mockResolvedValue([makeCase()]);
    getAuditTrailMock.mockResolvedValue(REALISTIC_TRAIL);
    render(<DecisionHistory />);
    await openCase(user);

    await screen.findByText("Flagged for review");
    const badges = timelineItems().map((li) => li.textContent ?? "");
    expect(badges[0]).toMatch(/flagged for review/i);
    expect(badges[1]).toMatch(/rejected/i);
    expect(badges[2]).toMatch(/accepted/i);

    // The same ordering, asserted on the machine-readable timestamps.
    const stamps = timelineItems().map((li) => li.querySelector("time")?.getAttribute("datetime"));
    expect(stamps).toEqual(["2026-08-20T11:00:00Z", "2026-08-21T09:00:00Z", "2026-08-22T14:30:00Z"]);
  });

  it("takes reviewer, decision, timestamp and notes from the audit event, not the case row", async () => {
    const user = userEvent.setup();
    // The case row carries only the LATEST decision, and a different reviewer
    // and notes than any single audit event -- so anything sourced from the
    // row instead of the trail shows up here.
    listCasesMock.mockResolvedValue([
      makeCase({ reviewer_decision: "accept", reviewer_name: "Row Reviewer", reviewer_notes: "row-level note" }),
    ]);
    getAuditTrailMock.mockResolvedValue(REALISTIC_TRAIL);
    render(<DecisionHistory />);
    await openCase(user);

    await screen.findByText("Flagged for review");
    const [first, second, third] = timelineItems();

    expect(within(first).getByText(/by priya r/i)).toBeInTheDocument();
    expect(within(first).getByText(/needs a second pass/i)).toBeInTheDocument();
    expect(first.querySelector("time")).toHaveAttribute("datetime", "2026-08-20T11:00:00Z");

    expect(within(second).getByText(/by akhilesh/i)).toBeInTheDocument();
    expect(within(second).getByText(/tampering indicators on page 2/i)).toBeInTheDocument();

    expect(within(third).getByText(/by agalya/i)).toBeInTheDocument();
    expect(within(third).getByText(/cleared after re-scan/i)).toBeInTheDocument();

    // Nothing from the cases table leaked into the history.
    expect(screen.queryByText(/row reviewer/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/row-level note/i)).not.toBeInTheDocument();
  });

  it("keys each decision on its own audit event id, so no decision is dropped", async () => {
    const user = userEvent.setup();
    listCasesMock.mockResolvedValue([makeCase()]);
    getAuditTrailMock.mockResolvedValue(REALISTIC_TRAIL);
    render(<DecisionHistory />);
    await openCase(user);

    await screen.findByText("Flagged for review");
    const ids = REALISTIC_TRAIL.filter((e) => e.event_type === "decision_recorded").map((e) => e.id);
    expect(new Set(ids).size).toBe(3);
    // Three distinct ids in, three rendered rows out -- none collapsed by a duplicate key.
    expect(timelineItems()).toHaveLength(3);
  });

  it("renders repeated identical decisions as separate entries", async () => {
    const user = userEvent.setup();
    listCasesMock.mockResolvedValue([makeCase()]);
    // Same decision, same second -- only the audit id separates them. This is
    // the real-backend case that `at`-based ordering or id-less keys would lose.
    getAuditTrailMock.mockResolvedValue([
      makeEvent({ id: "aud_same01", actor: "Priya R", detail: { decision: "review", notes: null }, at: "2026-08-20T11:00:00Z" }),
      makeEvent({ id: "aud_same02", actor: "Priya R", detail: { decision: "review", notes: null }, at: "2026-08-20T11:00:00Z" }),
    ]);
    render(<DecisionHistory />);
    await openCase(user);

    expect(await screen.findByText("2 decisions recorded")).toBeInTheDocument();
    expect(timelineItems()).toHaveLength(2);
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
