import { useEffect, useMemo, useState } from "react";
import { listCases } from "../api";
import type { CaseSummary, ReviewDecision, Severity } from "../types";
import { filterCases } from "../case-history-model";
import { stagger } from "../motion";

/** Local copy of the same label/color mapping ResultSummary.tsx uses for the
 *  full report -- kept local rather than importing from there, so this
 *  screen never has an editing reason to touch that already-shipped file. */
const SEVERITY_BADGE: Record<Severity, { label: string; classes: string }> = {
  low: { label: "Low", classes: "bg-emerald-50 text-emerald-800 border-emerald-200" },
  medium: { label: "Medium", classes: "bg-amber-50 text-amber-800 border-amber-200" },
  high: { label: "High", classes: "bg-rose-50 text-rose-800 border-rose-200" },
  critical: { label: "Critical", classes: "bg-purple-50 text-purple-800 border-purple-200" },
};

const DECISION_BADGE: Record<CaseSummary["recommendation_decision"], { label: string; classes: string }> = {
  accept: { label: "Accept", classes: "bg-emerald-600 text-white" },
  review: { label: "Human review", classes: "bg-amber-600 text-white" },
  reject: { label: "Reject", classes: "bg-rose-600 text-white" },
};

const REVIEWER_BADGE: Record<ReviewDecision, { label: string; classes: string }> = {
  accept: { label: "Accepted", classes: "bg-emerald-50 text-emerald-800 border-emerald-200" },
  review: { label: "Flagged for review", classes: "bg-amber-50 text-amber-800 border-amber-200" },
  reject: { label: "Rejected", classes: "bg-rose-50 text-rose-800 border-rose-200" },
};

function ReviewerStatusBadge({ decision }: { decision: ReviewDecision | null }) {
  if (decision === null) {
    return (
      <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-600">
        Pending
      </span>
    );
  }
  const b = REVIEWER_BADGE[decision];
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${b.classes}`}>
      {b.label}
    </span>
  );
}

interface CaseHistoryProps {
  /** Open the full, unmodified ReportView for this case (fetched via getCase). */
  onOpenCase: (reportId: string) => void;
  /** Return to the screen this was opened from (upload, or a report). */
  onBack: () => void;
}

export function CaseHistory({ onOpenCase, onBack }: CaseHistoryProps) {
  const [cases, setCases] = useState<CaseSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState<Severity | "all">("all");
  const [decision, setDecision] = useState<ReviewDecision | "pending" | "all">("all");

  useEffect(() => {
    const controller = new AbortController();
    listCases({ limit: 100 }, controller.signal)
      .then((result) => setCases(result))
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setCases(null);
        setError(err instanceof Error ? err.message : "Could not load case history.");
      });
    return () => controller.abort();
  }, []);

  const filtered = useMemo(
    () => (cases ? filterCases(cases, query, severity, decision) : []),
    [cases, query, severity, decision],
  );

  const hasActiveFilter = query.trim() !== "" || severity !== "all" || decision !== "all";

  return (
    <div className="mx-auto w-full max-w-6xl space-y-5 pb-20">
      <header className="eg-reveal">
        <button
          type="button"
          onClick={onBack}
          className="eg-press inline-flex min-h-[44px] flex-shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-lg border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 hover:border-guard-400 hover:text-guard-700 mb-3"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" /></svg>
          Back
        </button>
        <h1 className="text-lg font-bold tracking-tight text-slate-900">Case history</h1>
        <p className="mt-1 text-xs text-slate-500">
          {cases !== null && `${cases.length} case${cases.length === 1 ? "" : "s"} on record`}
        </p>
      </header>

      {error && (
        <div className="eg-scale-in eg-card border-rose-200 bg-rose-50 p-4 text-sm text-rose-700" role="alert">
          {error}
        </div>
      )}

      {!error && (
        <div className="eg-reveal eg-card p-4" style={stagger(1)}>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="flex-1">
              <label htmlFor="case-search" className="sr-only">
                Search by case or bundle ID
              </label>
              <input
                id="case-search"
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by case or bundle ID…"
                className="w-full rounded-md border border-slate-300 bg-slate-50 p-2.5 text-sm shadow-sm placeholder-slate-400 focus:border-guard-500 focus:ring-guard-500"
              />
            </div>
            <div className="flex flex-shrink-0 gap-2">
              <label className="sr-only" htmlFor="severity-filter">
                Filter by risk severity
              </label>
              <select
                id="severity-filter"
                value={severity}
                onChange={(e) => setSeverity(e.target.value as Severity | "all")}
                className="min-h-[42px] rounded-md border border-slate-300 bg-white px-2.5 text-sm text-slate-700 shadow-sm focus:border-guard-500 focus:ring-guard-500"
              >
                <option value="all">All severities</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>

              <label className="sr-only" htmlFor="decision-filter">
                Filter by reviewer status
              </label>
              <select
                id="decision-filter"
                value={decision}
                onChange={(e) => setDecision(e.target.value as ReviewDecision | "pending" | "all")}
                className="min-h-[42px] rounded-md border border-slate-300 bg-white px-2.5 text-sm text-slate-700 shadow-sm focus:border-guard-500 focus:ring-guard-500"
              >
                <option value="all">All statuses</option>
                <option value="pending">Pending</option>
                <option value="accept">Accepted</option>
                <option value="review">Flagged for review</option>
                <option value="reject">Rejected</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {!error && cases === null && (
        <div className="eg-card p-8 text-center text-sm text-slate-500" aria-live="polite">
          Loading past verifications…
        </div>
      )}

      {!error && cases !== null && cases.length === 0 && (
        <div className="eg-card p-8 text-center text-sm text-slate-500">
          No cases yet. Run a verification to see it appear here.
        </div>
      )}

      {!error && cases !== null && cases.length > 0 && filtered.length === 0 && (
        <div className="eg-card p-8 text-center text-sm text-slate-500">
          {hasActiveFilter ? "No cases match these filters." : "No cases yet."}
        </div>
      )}

      {!error && filtered.length > 0 && (
        <div className="eg-reveal eg-card overflow-hidden" style={stagger(2)}>
          <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Case
                </th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Date
                </th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Documents
                </th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Risk
                </th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Recommendation
                </th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Reviewer status
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {filtered.map((c) => {
                const sev = SEVERITY_BADGE[c.risk_severity];
                const dec = DECISION_BADGE[c.recommendation_decision];
                return (
                  <tr
                    key={c.report_id}
                    onClick={() => onOpenCase(c.report_id)}
                    className="signal-row cursor-pointer"
                  >
                    <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-700">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onOpenCase(c.report_id);
                        }}
                        className="eg-press rounded font-mono text-xs text-slate-700 hover:text-guard-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-guard-500"
                      >
                        {c.report_id}
                      </button>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-600">
                      {new Date(c.created_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-600">{c.document_count}</td>
                    <td className="whitespace-nowrap px-4 py-3">
                      <span className={`tabular inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium ${sev.classes}`}>
                        {Math.round(c.risk_score)} &middot; {sev.label}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold ${dec.classes}`}>
                        {dec.label}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      <ReviewerStatusBadge decision={c.reviewer_decision} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          </div>
        </div>
      )}
    </div>
  );
}
