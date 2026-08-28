import type { Reason } from "../report-model";
import { stagger } from "../motion";
import { Disclosure } from "./Disclosure";

const SOURCE_DOT: Record<Reason["source"], string> = {
  forensics: "bg-rose-500",
  metadata: "bg-amber-500",
  consistency: "bg-purple-500",
  ocr: "bg-slate-400",
};

function ReasonRow({ reason, rank }: { reason: Reason; rank: number }) {
  return (
    <li className="eg-slide-in flex gap-3" style={stagger(rank)}>
      <span className="mt-1.5 flex-shrink-0" aria-hidden="true">
        <span className={`block h-2 w-2 rounded-full ${SOURCE_DOT[reason.source]}`} />
      </span>
      <div className="min-w-0 flex-1">
        {/* WHAT happened */}
        <div className="flex items-baseline justify-between gap-3">
          <h3 className="text-sm font-semibold text-slate-900">{reason.what}</h3>
          <span className="tabular flex-shrink-0 text-xs font-semibold text-slate-500">
            +{reason.points.toFixed(1)}
          </span>
        </div>

        {/* WHERE it was found */}
        <p className="mt-0.5 text-xs text-slate-500">
          {reason.where ? (
            <span className="truncate">{reason.where}</span>
          ) : (
            <span>Across documents</span>
          )}
          <span aria-hidden="true"> · </span>
          {reason.sourceLabel}
        </p>

        {/* WHY it matters — the producing module's own words, verbatim. */}
        {reason.why && (
          <p className="mt-1.5 text-sm leading-relaxed text-slate-700">{reason.why}</p>
        )}
      </div>
    </li>
  );
}

export function TopReasons({ reasons }: { reasons: Reason[] }) {
  if (reasons.length === 0) {
    return (
      <section className="eg-card p-5" aria-labelledby="why-heading">
        <h2 id="why-heading" className="text-base font-bold text-slate-900">
          Why this result
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          No signal contributed to this score. Nothing was flagged — which is not the same as
          confirming the documents are genuine.
        </p>
      </section>
    );
  }

  const top = reasons.slice(0, 3);
  const rest = reasons.slice(3);
  const restPoints = rest.reduce((sum, r) => sum + r.points, 0);

  return (
    <section className="eg-card p-5" aria-labelledby="why-heading">
      <div className="mb-4 flex items-baseline justify-between gap-3">
        <h2 id="why-heading" className="text-base font-bold text-slate-900">
          Why this result
        </h2>
        <span className="text-xs text-slate-500">
          top {top.length} of {reasons.length}
        </span>
      </div>

      <ol className="space-y-4">
        {top.map((r, i) => (
          <ReasonRow key={`${r.signalId}-${r.documentId ?? "bundle"}`} reason={r} rank={i} />
        ))}
      </ol>

      {/* Weaker signals stay reachable — collapsed, never removed. */}
      {rest.length > 0 && (
        <div className="mt-4">
          <Disclosure
            summary={`${rest.length} further signal${rest.length === 1 ? "" : "s"}`}
            hint={`+${restPoints.toFixed(1)} pts combined`}
            tone="quiet"
          >
            <ol className="space-y-4">
              {rest.map((r, i) => (
                <ReasonRow key={`${r.signalId}-${r.documentId ?? "bundle"}`} reason={r} rank={i} />
              ))}
            </ol>
          </Disclosure>
        </div>
      )}
    </section>
  );
}
