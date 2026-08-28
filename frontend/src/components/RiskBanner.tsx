import { Risk, Severity } from "../types";
import { stagger, useCountUp, useReducedMotion } from "../motion";

interface RiskBannerProps {
  risk: Risk;
}

/* Severity carries meaning, so it is never signalled by colour alone: each
   band also has a distinct label, band range and icon (WCAG color-not-only). */
const SEVERITY: Record<
  Severity,
  { text: string; ring: string; surface: string; stroke: string; label: string; band: string }
> = {
  low: {
    text: "text-emerald-800",
    ring: "border-emerald-200",
    surface: "bg-emerald-50",
    stroke: "#059669",
    label: "Low risk",
    band: "0–24",
  },
  medium: {
    text: "text-amber-800",
    ring: "border-amber-200",
    surface: "bg-amber-50",
    stroke: "#b45309",
    label: "Medium risk",
    band: "25–49",
  },
  high: {
    text: "text-rose-800",
    ring: "border-rose-200",
    surface: "bg-rose-50",
    stroke: "#e11d48",
    label: "High risk",
    band: "50–74",
  },
  critical: {
    text: "text-purple-800",
    ring: "border-purple-200",
    surface: "bg-purple-50",
    stroke: "#7c3aed",
    label: "Critical risk",
    band: "75–100",
  },
};

const SEVERITY_PATH: Record<Severity, string> = {
  low: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  medium: "M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z",
  high: "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z",
  critical:
    "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z",
};

export function RiskBanner({ risk }: RiskBannerProps) {
  const s = SEVERITY[risk.severity];
  const reduced = useReducedMotion();
  const animatedScore = useCountUp(risk.score, 900);

  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  /* The arc sweeps from empty to the real score; with reduced motion it is
     rendered at its final position immediately. Presentation only — the value
     itself always comes straight from the backend. */
  const shown = reduced ? risk.score : animatedScore;
  const offset = circumference - (Math.min(100, Math.max(0, shown)) / 100) * circumference;

  const ranked = [...risk.contributions].sort((a, b) => b.contribution - a.contribution);
  const maxContribution = ranked.length > 0 ? ranked[0].contribution : 1;

  return (
    <section
      className={`eg-reveal overflow-hidden rounded-xl border ${s.ring} ${s.surface}`}
      aria-labelledby="risk-heading"
    >
      <div className="flex flex-col gap-6 p-5 sm:p-6 md:flex-row md:items-start">
        {/* ── Gauge ──────────────────────────────────────────────────── */}
        <div className="relative mx-auto flex h-32 w-32 flex-shrink-0 items-center justify-center md:mx-0">
          <svg className="h-full w-full -rotate-90" viewBox="0 0 100 100" aria-hidden="true">
            <circle cx="50" cy="50" r={radius} fill="none" stroke="#fff" strokeWidth="9" opacity="0.7" />
            <circle
              cx="50"
              cy="50"
              r={radius}
              fill="none"
              stroke={s.stroke}
              strokeWidth="9"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              className="risk-gauge"
            />
          </svg>
          <div className="absolute flex flex-col items-center">
            <span className={`tabular text-4xl font-bold leading-none ${s.text}`}>
              {Math.round(shown)}
            </span>
            <span
              className={`mt-1 text-[10px] font-semibold uppercase tracking-widest ${s.text} opacity-70`}
            >
              / 100
            </span>
          </div>
        </div>

        {/* ── Summary ────────────────────────────────────────────────── */}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <svg
              className={`h-5 w-5 ${s.text}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.8}
                d={SEVERITY_PATH[risk.severity]}
              />
            </svg>
            <h2 id="risk-heading" className={`text-xl font-bold tracking-tight ${s.text}`}>
              {s.label}
            </h2>
            <span
              className={`rounded-full border ${s.ring} bg-white/70 px-2 py-0.5 text-[11px] font-medium ${s.text}`}
            >
              band {s.band}
            </span>
          </div>

          <p className={`mt-1.5 text-sm ${s.text} opacity-80`}>
            {risk.contributions.length === 0
              ? "No signal contributed to this score."
              : `Fused from ${risk.contributions.length} signal${
                  risk.contributions.length === 1 ? "" : "s"
                }. Contributions below sum to the score.`}
          </p>

          {/* Proportional bars make relative weight readable at a glance,
              with the exact backend value kept alongside. */}
          {ranked.length > 0 ? (
            <ul className="mt-4 space-y-1.5">
              {ranked.map((c, i) => {
                const pct = maxContribution > 0 ? (c.contribution / maxContribution) * 100 : 0;
                const [signal, docId] = c.signal_id.split("@");
                return (
                  <li
                    key={`${c.signal_id}-${i}`}
                    className="eg-slide-in rounded-lg bg-white/70 px-3 py-2"
                    style={stagger(i)}
                  >
                    <div className="flex items-baseline justify-between gap-3">
                      <span
                        className="min-w-0 truncate text-sm font-medium text-slate-800"
                        title={c.signal_id}
                      >
                        {signal.replace(/_/g, " ")}
                        {docId ? (
                          <span className="ml-1.5 font-mono text-[11px] text-slate-500">{docId}</span>
                        ) : null}
                      </span>
                      <span className="tabular flex-shrink-0 text-xs font-semibold text-slate-600">
                        +{c.contribution.toFixed(1)} pts
                      </span>
                    </div>
                    <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-slate-200/70">
                      <div
                        className="eg-bar h-full rounded-full"
                        style={{ width: `${pct}%`, backgroundColor: s.stroke, opacity: 0.55 }}
                      />
                    </div>
                    <span className="sr-only">
                      source {c.source}, raw signal score {c.signal_score} of 100
                    </span>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="mt-4 rounded-lg bg-white/60 px-3 py-2 text-sm italic text-slate-600">
              No significant risk contributors detected.
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
