import type { Consistency, ConsistencyCheck } from "../types";
import { tallyConsistency } from "../report-model";
import { stagger } from "../motion";
import { Disclosure } from "./Disclosure";

const STATUS_CHIP: Record<ConsistencyCheck["status"], string> = {
  pass: "bg-emerald-100 text-emerald-800",
  warn: "bg-amber-100 text-amber-800",
  fail: "bg-rose-100 text-rose-800",
  not_applicable: "bg-slate-100 text-slate-600",
};

function Tally({ n, label, tone }: { n: number; label: string; tone: string }) {
  return (
    <div className={`rounded-lg px-3 py-2 ${tone}`}>
      <div className="tabular text-lg font-bold leading-none">{n}</div>
      <div className="mt-1 text-[11px] font-medium uppercase tracking-wide opacity-80">{label}</div>
    </div>
  );
}

function CheckDetail({ check }: { check: ConsistencyCheck }) {
  return (
    <div>
      <div className="flex items-start justify-between gap-3">
        <h4 className="text-sm font-semibold text-slate-900">{check.label}</h4>
        <span
          className={`flex-shrink-0 rounded px-2 py-0.5 text-[11px] font-bold uppercase ${STATUS_CHIP[check.status]}`}
        >
          {check.status.replace(/_/g, " ")}
        </span>
      </div>
      <p className="mt-1 text-sm leading-relaxed text-slate-600">{check.detail}</p>

      {check.observed.length > 0 && (
        <dl className="mt-2 space-y-1">
          {check.observed.map((obs, i) => (
            <div key={i} className="flex gap-2 text-xs">
              <dt className="flex-shrink-0 font-mono text-slate-500">{obs.document_id}</dt>
              <dd className="min-w-0 break-all font-medium text-slate-700">{obs.value}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}

export function ConsistencyPanel({ consistency }: { consistency: Consistency }) {
  const t = tallyConsistency(consistency);

  return (
    <section className="eg-card p-5" aria-labelledby="consistency-heading">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h2 id="consistency-heading" className="text-base font-bold text-slate-900">
          Cross-document consistency
        </h2>
        <span className="text-xs text-slate-500">{t.total} checks</span>
      </div>

      {/* Counts first — the shape of the result at a glance. Not-applicable is
          present for completeness but deliberately not emphasised. */}
      <div className="grid grid-cols-4 gap-2 text-center">
        <Tally n={t.fail} label="Fail" tone={t.fail > 0 ? "bg-rose-50 text-rose-800" : "bg-slate-50 text-slate-500"} />
        <Tally n={t.warn} label="Warn" tone={t.warn > 0 ? "bg-amber-50 text-amber-800" : "bg-slate-50 text-slate-500"} />
        <Tally n={t.pass} label="Pass" tone={t.pass > 0 ? "bg-emerald-50 text-emerald-800" : "bg-slate-50 text-slate-500"} />
        <Tally n={t.notApplicable} label="N/A" tone="bg-slate-50 text-slate-500" />
      </div>

      {t.notApplicable > 0 && (
        <p className="mt-2 text-xs text-slate-500">
          {t.notApplicable} check{t.notApplicable === 1 ? "" : "s"} had nothing to compare — usually a
          field only one document carries.
        </p>
      )}

      {/* Actionable findings inline; everything else collapsed but present. */}
      {t.actionable.length > 0 ? (
        <ul className="mt-4 space-y-3">
          {t.actionable.map((check, i) => (
            <li
              key={check.id}
              className="eg-slide-in rounded-lg border border-slate-200 p-3"
              style={stagger(i)}
            >
              <CheckDetail check={check} />
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 rounded-lg bg-emerald-50 px-3 py-2.5 text-sm text-emerald-800">
          No contradiction found between documents.
        </p>
      )}

      {t.rest.length > 0 && (
        <div className="mt-3">
          <Disclosure summary="All checks" count={t.total} tone="quiet">
            <ul className="space-y-3">
              {t.rest.map((check) => (
                <li key={check.id} className="border-b border-slate-100 pb-3 last:border-0 last:pb-0">
                  <CheckDetail check={check} />
                </li>
              ))}
            </ul>
          </Disclosure>
        </div>
      )}
    </section>
  );
}
