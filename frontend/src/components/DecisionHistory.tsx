import { useEffect, useMemo, useState } from "react";
import { listCases, getAuditTrail } from "../api";
import type { AuditEvent, CaseSummary, ReviewDecision } from "../types";
import { filterCases } from "../case-history-model";
import { stagger } from "../motion";

/** Local badge styling, matching the conventions already used elsewhere in
 *  the app (ResultSummary.tsx, CaseHistory.tsx) -- kept local rather than
 *  imported, so this screen never has an editing reason to touch those
 *  already-shipped files. */
const DECISION_BADGE: Record<ReviewDecision, { label: string; classes: string }> = {
  accept: { label: "Accepted", classes: "bg-emerald-50 text-emerald-800 border-emerald-200" },
  review: { label: "Flagged for review", classes: "bg-amber-50 text-amber-800 border-amber-200" },
  reject: { label: "Rejected", classes: "bg-rose-50 text-rose-800 border-rose-200" },
};

function isReviewDecision(value: unknown): value is ReviewDecision {
  return value === "accept" || value === "review" || value === "reject";
}

interface DecisionHistoryProps {
  /** Optional: return to wherever the user came from. Omitted -> no back link. */
  onBack?: () => void;
}

export function DecisionHistory({ onBack }: DecisionHistoryProps) {
  const [cases, setCases] = useState<CaseSummary[] | null>(null);
  const [casesError, setCasesError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [events, setEvents] = useState<AuditEvent[] | null>(null);
  const [eventsError, setEventsError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    listCases({ limit: 100 }, controller.signal)
      .then((result) => setCases(result))
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setCasesError(err instanceof Error ? err.message : "Could not load cases.");
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setEvents(null);
      setEventsError(null);
      return;
    }
    const controller = new AbortController();
    setEvents(null);
    setEventsError(null);
    getAuditTrail(selectedId, controller.signal)
      .then((result) => setEvents(result))
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setEventsError(err instanceof Error ? err.message : "Could not load decision history.");
      });
    return () => controller.abort();
  }, [selectedId]);

  const matches = useMemo(
    () => (cases ? filterCases(cases, query, "all", "all") : []),
    [cases, query],
  );

  // A case's decision history is every decision_recorded event, in the
  // order the backend already returns them (oldest first, real insertion
  // order -- see backend/app/audit.py). This is the actual gap this screen
  // fills: CaseSummary/CaseDetail only ever expose the LATEST decision, but
  // every earlier one a reviewer made is already stored and retrievable
  // here, never discarded.
  const decisionEvents = useMemo(
    () => (events ?? []).filter((e) => e.event_type === "decision_recorded"),
    [events],
  );

  const selectedCase = selectedId ? (cases ?? []).find((c) => c.report_id === selectedId) ?? null : null;

  return (
    <div className="mx-auto w-full max-w-4xl space-y-5 pb-20">
      <header className="eg-reveal">
        {onBack && (
          <button
            type="button"
            onClick={onBack}
            className="eg-press mb-2 inline-flex items-center gap-1 rounded text-sm font-medium text-slate-500 hover:text-guard-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-guard-500"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back
          </button>
        )}
        <h1 className="text-lg font-bold tracking-tight text-slate-900">Decision history</h1>
        <p className="mt-1 text-xs text-slate-500">
          Find a case to see every reviewer decision ever recorded on it, not just the latest one.
        </p>
      </header>

      {casesError && (
        <div className="eg-scale-in eg-card border-rose-200 bg-rose-50 p-4 text-sm text-rose-700" role="alert">
          {casesError}
        </div>
      )}

      {!casesError && (
        <div className="eg-reveal eg-card p-4" style={stagger(1)}>
          <label htmlFor="decision-case-search" className="mb-2 block text-xs font-semibold uppercase tracking-wide text-slate-500">
            Case
          </label>
          <input
            id="decision-case-search"
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedId(null);
            }}
            placeholder="Search by case or bundle ID…"
            className="w-full rounded-md border border-slate-300 bg-slate-50 p-2.5 text-sm shadow-sm placeholder-slate-400 focus:border-guard-500 focus:ring-guard-500"
          />

          {cases === null && !casesError && (
            <p className="mt-3 text-sm text-slate-500" aria-live="polite">
              Loading cases&hellip;
            </p>
          )}

          {cases !== null && query.trim() !== "" && !selectedId && (
            <ul className="mt-3 max-h-56 divide-y divide-slate-100 overflow-y-auto rounded-md border border-slate-100">
              {matches.length === 0 && (
                <li className="px-3 py-2 text-sm text-slate-500">No cases match &ldquo;{query}&rdquo;.</li>
              )}
              {matches.map((c) => (
                <li key={c.report_id}>
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedId(c.report_id);
                      setQuery(c.report_id);
                    }}
                    className="eg-press w-full px-3 py-2 text-left text-sm text-slate-700 hover:bg-guard-50 focus:outline-none focus-visible:bg-guard-50"
                  >
                    <span className="font-mono text-xs">{c.report_id}</span>
                    <span className="ml-2 text-xs text-slate-400">{c.document_count} document{c.document_count === 1 ? "" : "s"}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {selectedId && (
        <div className="eg-reveal eg-card p-5" style={stagger(2)}>
          <div className="mb-4 flex items-baseline justify-between gap-3">
            <div>
              <p className="font-mono text-xs text-slate-500">{selectedId}</p>
              {selectedCase && (
                <p className="text-xs text-slate-400">
                  {selectedCase.document_count} document{selectedCase.document_count === 1 ? "" : "s"} &middot;{" "}
                  {new Date(selectedCase.created_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}
                </p>
              )}
            </div>
            {events !== null && (
              <span className="whitespace-nowrap text-xs font-medium text-slate-500">
                {decisionEvents.length} decision{decisionEvents.length === 1 ? "" : "s"} recorded
              </span>
            )}
          </div>

          {eventsError && (
            <div className="eg-scale-in border-rose-200 bg-rose-50 p-3 text-sm text-rose-700" role="alert">
              {eventsError}
            </div>
          )}

          {!eventsError && events === null && (
            <p className="text-sm text-slate-500" aria-live="polite">
              Loading decision history&hellip;
            </p>
          )}

          {!eventsError && events !== null && decisionEvents.length === 0 && (
            <p className="text-sm text-slate-500">No decisions have been recorded for this case yet.</p>
          )}

          {!eventsError && decisionEvents.length > 0 && (
            <ol className="relative space-y-5 border-l border-slate-200 pl-5">
              {decisionEvents.map((event) => {
                const rawDecision = event.detail?.decision;
                const decision = isReviewDecision(rawDecision) ? rawDecision : null;
                const notes = typeof event.detail?.notes === "string" ? event.detail.notes : null;
                const badge = decision ? DECISION_BADGE[decision] : null;
                return (
                  <li key={event.id} className="relative">
                    <span className="absolute -left-[25px] top-1 h-2.5 w-2.5 rounded-full bg-guard-500 ring-4 ring-white" aria-hidden="true" />
                    <div className="flex flex-wrap items-center gap-2">
                      {badge ? (
                        <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${badge.classes}`}>
                          {badge.label}
                        </span>
                      ) : (
                        <span className="text-xs text-slate-500">Decision recorded</span>
                      )}
                      {event.actor && <span className="text-xs text-slate-500">by {event.actor}</span>}
                      <time className="text-xs text-slate-400" dateTime={event.at}>
                        {new Date(event.at).toLocaleString()}
                      </time>
                    </div>
                    {notes && <p className="mt-1.5 text-sm italic text-slate-600">&ldquo;{notes}&rdquo;</p>}
                  </li>
                );
              })}
            </ol>
          )}
        </div>
      )}
    </div>
  );
}
