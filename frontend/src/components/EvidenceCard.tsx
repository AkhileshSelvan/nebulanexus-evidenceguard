import type { ForensicSignal, MetadataSignal, ReportDocumentEntry } from "../types";
import { Disclosure } from "./Disclosure";
import { displayLabel, displayText, isInformationalSignal } from "../report-model";

/**
 * Per-document evidence, grouped by source with the important findings first.
 *
 * This replaced a tabbed layout. Tabs rendered only one section at a time, so
 * forensic and metadata findings were absent from the DOM until clicked —
 * invisible to find-in-page and to assistive tech, and two interactions deep
 * once the card itself sits inside a disclosure. Grouped sections keep every
 * finding present and collapse only the raw/technical parts.
 *
 * Nothing is filtered out: flagged, informational and passed findings are all
 * rendered, only ordered by how much they matter.
 */

type AnySignal = ForensicSignal | MetadataSignal;

/** A finding the analyzer recorded but deliberately did not score. */
function isInformational(s: AnySignal): boolean {
  return isInformationalSignal(s.detail);
}

function SignalRow({ signal }: { signal: AnySignal }) {
  const informational = isInformational(signal);
  const flagged = !signal.passed;

  const chip = flagged
    ? "bg-rose-100 text-rose-800"
    : informational
      ? "bg-slate-100 text-slate-600"
      : "bg-emerald-100 text-emerald-800";
  const chipLabel = flagged ? "Flagged" : informational ? "Informational" : "Pass";

  return (
    <li className="signal-row rounded-lg px-2.5 py-2">
      <div className="flex items-start justify-between gap-3">
        <span className="text-sm font-medium text-slate-800">{displayLabel(signal.label)}</span>
        <span className="flex flex-shrink-0 items-center gap-1.5">
          {flagged && (
            <span className="tabular text-xs font-semibold text-slate-500">
              {signal.score.toFixed(0)}
            </span>
          )}
          <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${chip}`}>
            {chipLabel}
          </span>
        </span>
      </div>
      {signal.detail && (
        <p className="mt-1 text-xs leading-relaxed text-slate-600">{displayText(signal.detail)}</p>
      )}
      {"regions" in signal && signal.regions.length > 0 && (
        <p className="mt-1 text-[11px] text-slate-500">
          {signal.regions.length} annotated region{signal.regions.length === 1 ? "" : "s"}
        </p>
      )}
    </li>
  );
}

/** Flagged first, then informational, then clean — each group by score desc. */
function rank(signals: AnySignal[]): AnySignal[] {
  const tier = (s: AnySignal) => (!s.passed ? 0 : isInformational(s) ? 1 : 2);
  return [...signals].sort((a, b) => tier(a) - tier(b) || b.score - a.score);
}

function SourceSection({
  title,
  summary,
  signals,
}: {
  title: string;
  summary: string;
  signals: AnySignal[];
}) {
  const ordered = rank(signals);
  const flagged = ordered.filter((s) => !s.passed);
  const others = ordered.filter((s) => s.passed);

  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between gap-2">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</h4>
        {flagged.length > 0 && (
          <span className="rounded-full bg-rose-100 px-1.5 py-0.5 text-[10px] font-bold text-rose-800">
            {flagged.length} flagged
          </span>
        )}
      </div>
      {summary && <p className="mb-2 text-xs text-slate-500">{displayText(summary)}</p>}

      {flagged.length > 0 && (
        <ul className="space-y-1">
          {flagged.map((s, i) => (
            <SignalRow key={`${s.id}-${i}`} signal={s} />
          ))}
        </ul>
      )}

      {others.length > 0 && (
        <div className={flagged.length > 0 ? "mt-2" : ""}>
          <Disclosure summary="Checks that did not flag" count={others.length} tone="quiet">
            <ul className="space-y-1">
              {others.map((s, i) => (
                <SignalRow key={`${s.id}-${i}`} signal={s} />
              ))}
            </ul>
          </Disclosure>
        </div>
      )}
    </div>
  );
}

export function EvidenceCard({ entry }: { entry: ReportDocumentEntry }) {
  const { document: doc, extraction, forensics, metadata } = entry;
  const rawEntries = Object.entries(metadata.raw ?? {});

  return (
    <div className="space-y-4">
      {/* Document facts — no internal id in the primary view. */}
      <p className="text-xs text-slate-500">
        {doc.detected_type?.replace(/_/g, " ") ?? "Unknown type"}
        <span aria-hidden="true"> · </span>
        {(doc.byte_size / 1024).toFixed(0)} KB
        <span aria-hidden="true"> · </span>
        {doc.page_count} page{doc.page_count === 1 ? "" : "s"}
      </p>

      <SourceSection title="Image forensics" summary={forensics.summary} signals={forensics.signals} />
      <SourceSection title="File metadata" summary={metadata.summary} signals={metadata.signals} />

      {/* Extracted text — technical, collapsed by default. */}
      <div>
        <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Document text
        </h4>
        <p className="mb-2 text-xs text-slate-500">
          {extraction.engine}
          <span aria-hidden="true"> · </span>
          confidence {(extraction.text_confidence * 100).toFixed(0)}%
          <span aria-hidden="true"> · </span>
          {extraction.fields.length} field{extraction.fields.length === 1 ? "" : "s"} extracted
        </p>

        {extraction.fields.length > 0 ? (
          <Disclosure summary="Extracted fields" count={extraction.fields.length} tone="quiet">
            <dl className="space-y-1.5">
              {extraction.fields.map((f, i) => (
                <div key={i} className="flex items-baseline gap-2 text-xs">
                  <dt className="w-28 flex-shrink-0 text-slate-500">{f.key.replace(/_/g, " ")}</dt>
                  <dd className="min-w-0 flex-1 break-words font-medium text-slate-800">{f.value}</dd>
                  <dd className="tabular flex-shrink-0 text-slate-500">
                    {Math.round(f.confidence * 100)}%
                  </dd>
                </div>
              ))}
            </dl>
          </Disclosure>
        ) : (
          <p className="rounded-lg bg-slate-50 px-2.5 py-2 text-xs italic text-slate-500">
            No fields extracted.
          </p>
        )}

        {extraction.warnings && extraction.warnings.length > 0 && (
          <div className="mt-2">
            <Disclosure summary="Extraction warnings" count={extraction.warnings.length} tone="quiet">
              <ul className="space-y-1">
                {extraction.warnings.map((w, i) => (
                  <li key={i} className="text-xs leading-relaxed text-slate-600">
                    {w}
                  </li>
                ))}
              </ul>
            </Disclosure>
          </div>
        )}
      </div>

      {/* Raw file properties — deepest technical level. */}
      {rawEntries.length > 0 && (
        <Disclosure summary="Raw file properties" count={rawEntries.length} tone="quiet">
          <dl className="space-y-1">
            {rawEntries.map(([k, v]) => (
              <div key={k} className="flex gap-2 text-[11px]">
                <dt className="w-32 flex-shrink-0 font-mono text-slate-500">{k}</dt>
                <dd className="min-w-0 break-all font-mono text-slate-700">{String(v)}</dd>
              </div>
            ))}
          </dl>
        </Disclosure>
      )}
    </div>
  );
}
