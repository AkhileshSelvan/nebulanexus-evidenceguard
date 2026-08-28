import type { Recommendation, Risk, Severity } from "../types";
import { useCountUp, useReducedMotion } from "../motion";

/**
 * The primary answer: what happened, and what should I do?
 *
 * Score, severity and recommendation all come straight from the backend and are
 * rendered unchanged. The count-up animates only the *presentation* of the
 * score the backend already returned.
 */

const SEVERITY: Record<
  Severity,
  { text: string; ring: string; surface: string; stroke: string; label: string; band: string }
> = {
  low: { text: "text-emerald-800", ring: "border-emerald-200", surface: "bg-emerald-50", stroke: "#059669", label: "Low risk", band: "0–24" },
  medium: { text: "text-amber-800", ring: "border-amber-200", surface: "bg-amber-50", stroke: "#b45309", label: "Medium risk", band: "25–49" },
  high: { text: "text-rose-800", ring: "border-rose-200", surface: "bg-rose-50", stroke: "#e11d48", label: "High risk", band: "50–74" },
  critical: { text: "text-purple-800", ring: "border-purple-200", surface: "bg-purple-50", stroke: "#7c3aed", label: "Critical risk", band: "75–100" },
};

const DECISION: Record<Recommendation["decision"], { label: string; chip: string; path: string }> = {
  accept: {
    label: "Accept",
    chip: "bg-emerald-600 text-white",
    path: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  },
  review: {
    label: "Human review",
    chip: "bg-amber-600 text-white",
    path: "M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z",
  },
  reject: {
    label: "Reject",
    chip: "bg-rose-600 text-white",
    path: "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z",
  },
};

/** The disclaimer the product must always carry, kept beside the verdict. */
const DISCLAIMER = "This is a prompt for human review, not a determination of fraud.";

export function ResultSummary({
  risk,
  recommendation,
  headline,
}: {
  risk: Risk;
  recommendation: Recommendation;
  /** One short sentence from the backend explanation. */
  headline: string;
}) {
  const s = SEVERITY[risk.severity];
  const d = DECISION[recommendation.decision];
  const reduced = useReducedMotion();
  const animated = useCountUp(risk.score, 900);
  const shown = reduced ? risk.score : animated;

  const radius = 42;
  const circ = 2 * Math.PI * radius;
  const offset = circ - (Math.min(100, Math.max(0, shown)) / 100) * circ;

  return (
    <section className={`eg-reveal overflow-hidden rounded-xl border ${s.ring} ${s.surface}`} aria-labelledby="result-heading">
      <div className="flex flex-col gap-5 p-5 sm:p-6 md:flex-row md:items-center">
        {/* Score */}
        <div className="relative mx-auto flex h-32 w-32 flex-shrink-0 items-center justify-center md:mx-0">
          <svg className="h-full w-full -rotate-90" viewBox="0 0 100 100" aria-hidden="true">
            <circle cx="50" cy="50" r={radius} fill="none" stroke="#fff" strokeWidth="9" opacity="0.7" />
            <circle
              cx="50" cy="50" r={radius} fill="none" stroke={s.stroke} strokeWidth="9" strokeLinecap="round"
              strokeDasharray={circ} strokeDashoffset={offset} className="risk-gauge"
            />
          </svg>
          <div className="absolute flex flex-col items-center">
            <span className={`tabular text-4xl font-bold leading-none ${s.text}`}>{Math.round(shown)}</span>
            <span className={`mt-1 text-[10px] font-semibold uppercase tracking-widest ${s.text} opacity-70`}>/ 100</span>
          </div>
        </div>

        {/* Verdict */}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 id="result-heading" className={`text-2xl font-bold tracking-tight ${s.text}`}>
              {s.label}
            </h2>
            <span className={`rounded-full border ${s.ring} bg-white/70 px-2 py-0.5 text-[11px] font-medium ${s.text}`}>
              band {s.band}
            </span>
          </div>

          {/* Recommendation — the action, stated once, prominently. */}
          <div className="mt-3 flex flex-wrap items-center gap-2.5">
            <span className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-semibold ${d.chip}`}>
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={d.path} />
              </svg>
              {d.label}
            </span>
            <span className={`text-sm ${s.text} opacity-80`}>{recommendation.headline}</span>
          </div>

          {/* One-sentence plain-language explanation. */}
          <p className={`mt-3 text-sm leading-relaxed ${s.text} opacity-90`}>{headline}</p>

          <p className="mt-3 flex items-start gap-1.5 text-xs leading-relaxed text-slate-600">
            <svg className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
            </svg>
            <span>{DISCLAIMER}</span>
          </p>
        </div>
      </div>
    </section>
  );
}
