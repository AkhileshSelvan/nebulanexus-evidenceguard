import type { DocumentSummary } from "../report-model";
import type { Severity } from "../types";
import { stagger } from "../motion";
import { Disclosure } from "./Disclosure";
import { EvidenceCard } from "./EvidenceCard";

const SEVERITY_CHIP: Record<Severity, string> = {
  low: "bg-emerald-100 text-emerald-800",
  medium: "bg-amber-100 text-amber-800",
  high: "bg-rose-100 text-rose-800",
  critical: "bg-purple-100 text-purple-800",
};

function DocumentRow({ doc, index }: { doc: DocumentSummary; index: number }) {
  return (
    <li className="eg-slide-in" style={stagger(index)}>
      <Disclosure
        summary={doc.filename}
        hint={doc.topIssue ?? (doc.flaggedCount === 0 ? "no findings" : undefined)}
      >
        {/* The full per-document evidence view lives here, unchanged. */}
        <EvidenceCard entry={doc.entry} />
      </Disclosure>
    </li>
  );
}

function AttentionRow({ doc, index }: { doc: DocumentSummary; index: number }) {
  return (
    <li className="eg-slide-in" style={stagger(index)}>
      <details className="group rounded-lg border border-slate-200 bg-white">
        <summary className="eg-press flex min-h-[44px] cursor-pointer list-none items-center gap-3 rounded-lg px-3 py-2.5 hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-guard-600">
          <svg
            className="h-4 w-4 flex-shrink-0 text-slate-400 transition-transform duration-200 group-open:rotate-90"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>

          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-medium text-slate-900">{doc.filename}</span>
            <span className="block truncate text-xs text-slate-500">
              {doc.topIssue ?? "No flagged findings"}
              {doc.flaggedCount > 1 && (
                <span className="text-slate-500"> +{doc.flaggedCount - 1} more</span>
              )}
            </span>
          </span>

          <span
            className={`tabular flex-shrink-0 rounded px-2 py-1 text-xs font-bold ${SEVERITY_CHIP[doc.severity]}`}
          >
            {Math.round(doc.riskScore)}
          </span>
        </summary>
        <div className="border-t border-slate-100 p-3">
          <EvidenceCard entry={doc.entry} />
        </div>
      </details>
    </li>
  );
}

export function DocumentsPanel({ documents }: { documents: DocumentSummary[] }) {
  const attention = documents.filter((d) => d.needsAttention);
  const clean = documents.filter((d) => !d.needsAttention);

  return (
    <section className="eg-card p-5" aria-labelledby="docs-heading">
      <div className="mb-4 flex items-baseline justify-between gap-3">
        <h2 id="docs-heading" className="text-base font-bold text-slate-900">
          Documents
        </h2>
        <span className="text-xs text-slate-500">
          {attention.length > 0
            ? `${attention.length} of ${documents.length} need attention`
            : `${documents.length} document${documents.length === 1 ? "" : "s"}, none flagged`}
        </span>
      </div>

      {attention.length > 0 ? (
        <ul className="space-y-2">
          {attention.map((d, i) => (
            <AttentionRow key={d.entry.document.id} doc={d} index={i} />
          ))}
        </ul>
      ) : (
        <p className="rounded-lg bg-slate-50 px-3 py-2.5 text-sm text-slate-600">
          No document raised a scored finding.
        </p>
      )}

      {/* Everything else is still one click away. */}
      {clean.length > 0 && (
        <div className="mt-3">
          <Disclosure
            summary={`View all documents`}
            count={documents.length}
            tone="quiet"
          >
            <ul className="space-y-2">
              {clean.map((d, i) => (
                <DocumentRow key={d.entry.document.id} doc={d} index={i} />
              ))}
            </ul>
          </Disclosure>
        </div>
      )}
    </section>
  );
}
