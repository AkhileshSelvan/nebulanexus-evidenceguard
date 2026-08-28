import { RiskResult, Severity } from "../types";

interface RiskBannerProps {
  risk: RiskResult;
}

const SEVERITY_STYLES: Record<Severity, { text: string; bg: string; fill: string }> = {
  low: { text: "text-emerald-700", bg: "bg-emerald-50 border-emerald-200", fill: "#10b981" },
  medium: { text: "text-amber-700", bg: "bg-amber-50 border-amber-200", fill: "#f59e0b" },
  high: { text: "text-rose-700", bg: "bg-rose-50 border-rose-200", fill: "#ef4444" },
  critical: { text: "text-purple-700", bg: "bg-purple-50 border-purple-200", fill: "#7c3aed" },
};

export function RiskBanner({ risk }: RiskBannerProps) {
  const styles = SEVERITY_STYLES[risk.severity];
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (risk.score / 100) * circumference;

  return (
    <section className={`flex flex-col md:flex-row items-center gap-6 p-6 rounded-xl border ${styles.bg} transition-all`}>
      {/* Risk Gauge */}
      <div className="relative w-28 h-28 flex-shrink-0 flex items-center justify-center">
        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            className="text-white/50"
          />
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke={styles.fill}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            className="risk-gauge"
          />
        </svg>
        <div className="absolute flex flex-col items-center justify-center">
          <span className={`text-3xl font-bold ${styles.text}`}>{Math.round(risk.score)}</span>
          <span className={`text-xs font-medium uppercase tracking-widest ${styles.text} opacity-80`}>Risk</span>
        </div>
      </div>

      {/* Info & Contributions */}
      <div className="flex-1 w-full">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h2 className={`text-xl font-bold ${styles.text} capitalize mb-1`}>
              {risk.severity} Risk Bundle
            </h2>
            <p className={`text-sm ${styles.text} opacity-80`}>
              Aggregated across {risk.contributions.length} signals
            </p>
          </div>
        </div>

        {risk.contributions.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {risk.contributions.map((c, i) => (
              <div key={i} className="flex justify-between items-center bg-white/60 px-3 py-2 rounded shadow-sm text-sm">
                <span className="font-medium text-slate-700 truncate mr-2" title={c.signal_id}>
                  {c.signal_id.replace(/_/g, " ")}
                </span>
                <span className="font-mono text-slate-500 text-xs shrink-0">
                  +{c.contribution.toFixed(1)} pts
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500 italic bg-white/50 px-3 py-2 rounded">
            No significant risk contributors detected.
          </p>
        )}
      </div>
    </section>
  );
}
