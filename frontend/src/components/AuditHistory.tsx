import { useEffect, useState } from "react";
import { getAuditTrail } from "../api";
import type { AuditEvent } from "../types";

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
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 mt-6">
      <h2 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
        <svg className="w-5 h-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Audit history
      </h2>

      {error && (
        <p className="text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-md px-3 py-2">{error}</p>
      )}

      {!error && events === null && (
        <p className="text-sm text-slate-500 italic">Loading audit trail…</p>
      )}

      {!error && events !== null && events.length === 0 && (
        <p className="text-sm text-slate-500 italic">No audit events yet.</p>
      )}

      {!error && events !== null && events.length > 0 && (
        <div className="relative pl-4 border-l border-slate-200 space-y-6">
          {events.map((event) => (
            <div key={event.id} className="relative">
              <div className={`absolute -left-[21px] w-2.5 h-2.5 rounded-full ring-4 ring-white ${eventDotClass(event)}`} />

              <div className="flex flex-col sm:flex-row sm:items-baseline justify-between mb-1">
                <h4 className="text-sm font-semibold text-slate-800">{EVENT_LABEL[event.event_type]}</h4>
                <time className="text-xs text-slate-500" dateTime={event.at}>
                  {new Date(event.at).toLocaleString()}
                </time>
              </div>

              {event.actor && <p className="text-xs text-slate-500 mb-2">By {event.actor}</p>}

              {eventDetailText(event) && (
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 text-sm text-slate-700">
                  {eventDetailText(event)}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
