import { useMemo, useState } from "react";
import type { VerificationReport } from "../types";
import { buildReasons, summariseDocuments } from "../report-model";
import { ResultSummary } from "./ResultSummary";
import { TopReasons } from "./TopReasons";
import { DocumentsPanel } from "./DocumentsPanel";
import { ConsistencyPanel } from "./ConsistencyPanel";
import { ExplanationPanel } from "./ExplanationPanel";
import { ReviewerActions } from "./ReviewerActions";
import { AuditHistory } from "./AuditHistory";
import { Disclosure } from "./Disclosure";
import { stagger } from "../motion";

/**
 * Information architecture, in reading order:
 *
 *   1. RESULT      score + severity + recommendation + one-line explanation
 *   2. ACTION      Accept / Request evidence / Reject, reachable immediately
 *   3. WHY         top 3 reasons (what / where / why it matters)
 *   4. DOCUMENTS   those needing attention first
 *   5. CONSISTENCY counts, then actionable checks
 *   6. DETAIL      full narrative, glossary, audit — all collapsed
 *
 * Nothing is removed: every signal, field and raw property remains reachable
 * through the disclosures below. Only placement changed.
 */

/** First sentence of the backend summary — the plain-language "what happened". */
function leadSentence(summary: string): string {
  const trimmed = summary.trim();
  const end = trimmed.indexOf(". ");
  return end === -1 ? trimmed : trimmed.slice(0, end + 1);
}

export function ReportView({
  report,
  onReset,
  onBackToHistory,
}: {
  report: VerificationReport;
  onReset: () => void;
  /**
   * Present only when this report was opened from Case History, so the reader
   * gets the way back they actually came by. Purely navigational -- it does not
   * touch the report's contents.
   */
  onBackToHistory?: () => void;
}) {
  // Bumped after a decision is recorded so <AuditHistory> refetches the real
  // trail from the backend -- there is no client-side audit log anymore.
  const [auditRefreshToken, setAuditRefreshToken] = useState(0);

  const reasons = useMemo(() => buildReasons(report), [report]);
  const documents = useMemo(() => summariseDocuments(report), [report]);

  const partial = report.status !== "complete" || report.errors.length > 0;

  return (
    <div className="mx-auto w-full max-w-6xl space-y-5 pb-20">
      {/* ── Header ───────────────────────────────────────────────────── */}
      {onBackToHistory && (
        <button
          type="button"
          onClick={onBackToHistory}
          className="eg-press inline-flex min-h-[44px] flex-shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-lg border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 hover:border-guard-400 hover:text-guard-700 eg-reveal"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" /></svg>
          Back to case history
        </button>
      )}

      <header className="eg-reveal flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-lg font-bold tracking-tight text-slate-900">
              Verification report
            </h1>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-slate-600">
              Triage · for human review
            </span>
          </div>
          <p className="mt-1 truncate text-xs text-slate-500">
            {report.bundle.document_count} document
            {report.bundle.document_count === 1 ? "" : "s"}
            <span aria-hidden="true"> · </span>
            {new Date(report.created_at).toLocaleString()}
          </p>
        </div>
        <button
          type="button"
          onClick={onReset}
          className="eg-press inline-flex min-h-[44px] flex-shrink-0 items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 hover:border-guard-400 hover:text-guard-700"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New verification
        </button>
      </header>

      {partial && (
        <div
          className="eg-reveal rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
          style={stagger(1)}
          role="status"
        >
          <span className="font-semibold">Partial analysis.</span>{" "}
          {report.errors.length > 0
            ? `${report.errors.length} module error${
                report.errors.length === 1 ? "" : "s"
              } occurred; the sections that did run are still valid.`
            : `Report status is "${report.status}".`}
        </div>
      )}

      {/* ── 1. RESULT ────────────────────────────────────────────────── */}
      <ResultSummary
        risk={report.risk}
        recommendation={report.recommendation}
        headline={leadSentence(report.explanation.summary)}
      />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="space-y-5 lg:col-span-2">
          {/* ── 3. WHY ───────────────────────────────────────────────── */}
          <div className="eg-reveal" style={stagger(2)}>
            <TopReasons reasons={reasons} />
          </div>

          {/* ── 4. DOCUMENTS ─────────────────────────────────────────── */}
          <div className="eg-reveal" style={stagger(3)}>
            <DocumentsPanel documents={documents} />
          </div>

          {/* ── 5. CONSISTENCY ───────────────────────────────────────── */}
          <div className="eg-reveal" style={stagger(4)}>
            <ConsistencyPanel consistency={report.consistency} />
          </div>

          {/* ── 6. TECHNICAL DETAIL — collapsed ──────────────────────── */}
          <div className="eg-reveal space-y-2" style={stagger(5)}>
            <h2 className="px-1 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Technical detail
            </h2>

            <Disclosure summary="Full explanation and glossary" tone="quiet">
              <ExplanationPanel explanation={report.explanation} />
            </Disclosure>

            {report.recommendation.suggested_actions.length > 0 && (
              <Disclosure
                summary="Suggested next steps"
                count={report.recommendation.suggested_actions.length}
                tone="quiet"
              >
                <ul className="space-y-2">
                  {report.recommendation.suggested_actions.map((a, i) => (
                    <li key={i} className="flex gap-2 text-sm text-slate-700">
                      <span className="mt-2 h-1 w-1 flex-shrink-0 rounded-full bg-slate-400" aria-hidden="true" />
                      <span>{a}</span>
                    </li>
                  ))}
                </ul>
              </Disclosure>
            )}

            <Disclosure summary="Reason codes" count={report.recommendation.reasons.length} tone="quiet">
              <ul className="space-y-2">
                {report.recommendation.reasons.map((r, i) => (
                  <li key={i} className="font-mono text-xs leading-relaxed text-slate-600">
                    {r}
                  </li>
                ))}
              </ul>
            </Disclosure>

            <Disclosure summary="Report identifiers" tone="quiet">
              <dl className="space-y-1.5 text-xs">
                <div className="flex gap-2">
                  <dt className="w-24 flex-shrink-0 text-slate-500">Report ID</dt>
                  <dd className="font-mono text-slate-700">{report.report_id}</dd>
                </div>
                <div className="flex gap-2">
                  <dt className="w-24 flex-shrink-0 text-slate-500">Bundle ID</dt>
                  <dd className="font-mono text-slate-700">{report.bundle.bundle_id}</dd>
                </div>
                <div className="flex gap-2">
                  <dt className="w-24 flex-shrink-0 text-slate-500">Status</dt>
                  <dd className="text-slate-700">{report.status}</dd>
                </div>
                <div className="flex gap-2">
                  <dt className="w-24 flex-shrink-0 text-slate-500">Risk model</dt>
                  <dd className="text-slate-700">
                    {report.risk.model.method} v{report.risk.model.version}
                  </dd>
                </div>
              </dl>
            </Disclosure>
          </div>
        </div>

        {/* ── 2. ACTION + 7. AUDIT — sticky rail ───────────────────── */}
        <div className="space-y-5">
          <div className="lg:sticky lg:top-24 lg:space-y-5">
            <div className="eg-reveal" style={stagger(2)}>
              <ReviewerActions
                reportId={report.report_id}
                onDecisionRecorded={() => setAuditRefreshToken((n) => n + 1)}
              />
            </div>
            <div className="eg-reveal" style={stagger(3)}>
              <AuditHistory reportId={report.report_id} refreshToken={auditRefreshToken} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
