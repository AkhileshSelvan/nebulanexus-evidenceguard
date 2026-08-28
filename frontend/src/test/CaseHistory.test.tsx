import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CaseHistory } from "../components/CaseHistory";
import type { CaseSummary } from "../types";

const { listCasesMock } = vi.hoisted(() => ({ listCasesMock: vi.fn() }));
vi.mock("../api", () => ({ listCases: listCasesMock }));

function makeCase(overrides: Partial<CaseSummary> = {}): CaseSummary {
  return {
    report_id: "rep_alpha001",
    bundle_id: "bnd_x1",
    created_at: "2026-08-20T10:00:00Z",
    status: "complete",
    document_count: 3,
    risk_score: 42,
    risk_severity: "medium",
    recommendation_decision: "review",
    reviewer_decision: null,
    reviewer_name: null,
    reviewer_notes: null,
    reviewed_at: null,
    ...overrides,
  };
}

describe("CaseHistory", () => {
  beforeEach(() => {
    listCasesMock.mockReset();
  });

  it("shows a loading state, then the fetched cases", async () => {
    listCasesMock.mockResolvedValue([makeCase()]);
    render(<CaseHistory onOpenCase={vi.fn()} />);

    expect(screen.getByText(/loading past verifications/i)).toBeInTheDocument();

    expect(await screen.findByText("rep_alpha001")).toBeInTheDocument();
    expect(screen.getByText(/42/)).toBeInTheDocument();
    expect(screen.getByText("Medium")).toBeInTheDocument();
    expect(screen.getByText("Human review")).toBeInTheDocument();
    expect(within(screen.getByRole("table")).getByText("Pending")).toBeInTheDocument();
  });

  it("shows an already-recorded reviewer decision, not just Pending", async () => {
    listCasesMock.mockResolvedValue([
      makeCase({ reviewer_decision: "accept", reviewer_name: "Priya R" }),
    ]);
    render(<CaseHistory onOpenCase={vi.fn()} />);

    expect(await screen.findByText("Accepted")).toBeInTheDocument();
    expect(within(screen.getByRole("table")).queryByText("Pending")).not.toBeInTheDocument();
  });

  it("shows an empty state when there are no cases at all", async () => {
    listCasesMock.mockResolvedValue([]);
    render(<CaseHistory onOpenCase={vi.fn()} />);

    expect(await screen.findByText(/no cases yet/i)).toBeInTheDocument();
  });

  it("shows an honest error state, never a fabricated list, when the fetch fails", async () => {
    listCasesMock.mockRejectedValue(new Error("List cases failed: backend responded 500"));
    render(<CaseHistory onOpenCase={vi.fn()} />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/backend responded 500/i);
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("filters rows by search text against report_id", async () => {
    const user = userEvent.setup();
    listCasesMock.mockResolvedValue([
      makeCase({ report_id: "rep_alpha001" }),
      makeCase({ report_id: "rep_beta002", bundle_id: "bnd_x2" }),
    ]);
    render(<CaseHistory onOpenCase={vi.fn()} />);

    await screen.findByText("rep_alpha001");
    expect(screen.getByText("rep_beta002")).toBeInTheDocument();

    await user.type(screen.getByLabelText(/search by case or bundle id/i), "alpha");

    expect(screen.getByText("rep_alpha001")).toBeInTheDocument();
    expect(screen.queryByText("rep_beta002")).not.toBeInTheDocument();
  });

  it("filters rows by severity", async () => {
    const user = userEvent.setup();
    listCasesMock.mockResolvedValue([
      makeCase({ report_id: "rep_low", risk_severity: "low" }),
      makeCase({ report_id: "rep_high", risk_severity: "high" }),
    ]);
    render(<CaseHistory onOpenCase={vi.fn()} />);

    await screen.findByText("rep_low");
    await user.selectOptions(screen.getByLabelText(/filter by risk severity/i), "high");

    expect(screen.queryByText("rep_low")).not.toBeInTheDocument();
    expect(screen.getByText("rep_high")).toBeInTheDocument();
  });

  it("filters rows by reviewer decision status", async () => {
    const user = userEvent.setup();
    listCasesMock.mockResolvedValue([
      makeCase({ report_id: "rep_pending", reviewer_decision: null }),
      makeCase({ report_id: "rep_rejected", reviewer_decision: "reject" }),
    ]);
    render(<CaseHistory onOpenCase={vi.fn()} />);

    await screen.findByText("rep_pending");
    expect(screen.getByText("rep_rejected")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/filter by reviewer status/i), "reject");

    expect(screen.queryByText("rep_pending")).not.toBeInTheDocument();
    expect(screen.getByText("rep_rejected")).toBeInTheDocument();
  });

  it("shows a no-matches message when filters exclude every case", async () => {
    const user = userEvent.setup();
    listCasesMock.mockResolvedValue([makeCase({ risk_severity: "low" })]);
    render(<CaseHistory onOpenCase={vi.fn()} />);

    await screen.findByText("rep_alpha001");
    await user.selectOptions(screen.getByLabelText(/filter by risk severity/i), "critical");

    expect(await screen.findByText(/no cases match these filters/i)).toBeInTheDocument();
  });

  it("calls onOpenCase with the report id when the case button is clicked", async () => {
    const user = userEvent.setup();
    const onOpenCase = vi.fn();
    listCasesMock.mockResolvedValue([makeCase({ report_id: "rep_click_me" })]);
    render(<CaseHistory onOpenCase={onOpenCase} />);

    const button = await screen.findByRole("button", { name: "rep_click_me" });
    await user.click(button);

    expect(onOpenCase).toHaveBeenCalledWith("rep_click_me");
  });

  it("opens a case on Enter as well as click, for keyboard users", async () => {
    const user = userEvent.setup();
    const onOpenCase = vi.fn();
    listCasesMock.mockResolvedValue([makeCase({ report_id: "rep_keyboard" })]);
    render(<CaseHistory onOpenCase={onOpenCase} />);

    const button = await screen.findByRole("button", { name: "rep_keyboard" });
    button.focus();
    await user.keyboard("{Enter}");

    expect(onOpenCase).toHaveBeenCalledWith("rep_keyboard");
  });

  it("also opens the case when the row itself is clicked (mouse convenience)", async () => {
    const user = userEvent.setup();
    const onOpenCase = vi.fn();
    listCasesMock.mockResolvedValue([makeCase({ report_id: "rep_row_click" })]);
    render(<CaseHistory onOpenCase={onOpenCase} />);

    await screen.findByText("rep_row_click");
    const cell = screen.getByText(/3/, { selector: "td" }); // document_count cell, not the button
    await user.click(cell);

    expect(onOpenCase).toHaveBeenCalledWith("rep_row_click");
  });
});
