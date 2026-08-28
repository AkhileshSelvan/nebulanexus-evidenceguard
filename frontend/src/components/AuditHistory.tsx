import { useEffect, useState } from "react";
import { getAuditTrail } from "../api";
import type { AuditEvent } from "../types";
import { stagger } from "../motion";

const EVENT_LABEL: Record<AuditEvent["event_type"], string> = {
  report_created: "Report created",
  decision_recorded: "Decision recorded",
};

function eventDotClass(event: AuditEvent): string {
  const decision = event.detail?.decision;
  if (decision === "accept") return "bg-emerald-500";
  if (decision === "reject") return "bg-rose-500";
  if (decision === "review") return "bg-amber-500";
  return "bg-guard-500"; // report_created / anything without a decision
}

function eventDetailText(event: AuditEvent): string | null {
  const parts: string[] = [];
  if (typeof event.detail?.decision === "string") parts.push(`Decision: ${event.detail.decision}`);
  if (typeof event.detail?.notes === "string" && event.detail.notes) parts.push(`"${event.detail.notes}"`);
  return parts.length ? parts.join(" — ") : null;
}

/**
 * Fetches and displays the case's REAL audit trail from the backend
 * (GET /api/v1/cases/{report_id}/audit) — this is never client-only state.
 * `refreshToken` changes (e.g. after a decision is recorded) trigger a refetch.
 */
export function AuditHistory({ reportId, refreshToken }: { reportId: string; refreshToken: number }) {
  const [events, setEvents] = useState<AuditEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setError(null);
    getAuditTrail(reportId, controller.signal)
      .then((evts) => setEvents(evts))
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setEvents(null);
        setError(err instanceof Error ? err.message : "Could not load the audit trail.");
      });
    return () => controller.abort();
  }, [reportId, refreshToken]);

  return (
    <div className="eg-card p-5">
      <h2 className="mb-4 flex items-center gap-2 text-base font-bold text-slate-900">
        <svg className="w-5 h-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Audit history
        {events && events.length > 0 ? (
          <span className="ml-auto rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
            {events.length}
          </span>
        ) : null}
      </h2>

      {error && (
        <p className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert">
          {error}
        </p>
      )}

      {!error && events === null && (
        /* Skeleton rather than a bare spinner, so the panel does not jump
           height when the real events land. */
        <div className="space-y-3" aria-live="polite" aria-busy="true">
          <span className="sr-only">Loading audit trail</span>
          {[0, 1].map((i) => (
            <div key={i} className="flex gap-3">
              <span className="mt-1 h-2.5 w-2.5 flex-shrink-0 animate-pulse rounded-full bg-slate-200" />
              <div className="flex-1 space-y-2">
                <div className="h-3 w-1/2 animate-pulse rounded bg-slate-200" />
                <div className="h-3 w-1/3 animate-pulse rounded bg-slate-100" />
              </div>
            </div>
          ))}
        </div>
      )}

      {!error && events !== null && events.length === 0 && (
        <p className="text-sm italic text-slate-500">No audit events yet.</p>
      )}

      {!error && events !== null && events.length > 0 && (
        <ol className="relative space-y-5 border-l border-slate-200 pl-4">
          {events.map((event, i) => (
            <li key={event.id} className="eg-slide-in relative" style={stagger(i)}>
              <span
                className={`absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full ring-4 ring-white ${eventDotClass(event)}`}
                aria-hidden="true"
              />

              <div className="mb-1 flex flex-col justify-between sm:flex-row sm:items-baseline sm:gap-2">
                <h4 className="text-sm font-semibold text-slate-800">
                  {EVENT_LABEL[event.event_type]}
                </h4>
                <time className="tabular flex-shrink-0 text-xs text-slate-500" dateTime={event.at}>
                  {new Date(event.at).toLocaleString()}
                </time>
              </div>

              {event.actor && <p className="mb-2 text-xs text-slate-500">By {event.actor}</p>}

              {eventDetailText(event) && (
                <div className="rounded-lg border border-slate-100 bg-slate-50 p-3 text-sm text-slate-700">
                  {eventDetailText(event)}
                </div>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
