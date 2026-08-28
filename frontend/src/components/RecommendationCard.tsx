import { Recommendation, ReviewDecision } from "../types";

interface RecommendationCardProps {
  recommendation: Recommendation;
}

const DECISION_META: Record<ReviewDecision, { icon: JSX.Element; color: string; label: string }> = {
  accept: {
    icon: (
      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    color: "text-emerald-600 bg-emerald-50 border-emerald-200",
    label: "Accept",
  },
  review: {
    icon: (
      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
    color: "text-amber-600 bg-amber-50 border-amber-200",
    label: "Manual Review",
  },
  reject: {
    icon: (
      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    color: "text-rose-600 bg-rose-50 border-rose-200",
    label: "Reject",
  },
};

export function RecommendationCard({ recommendation }: RecommendationCardProps) {
  const meta = DECISION_META[recommendation.decision];

  return (
    <div className="eg-card overflow-hidden">
      <div className={`p-5 border-b flex items-start gap-4 ${meta.color}`}>
        <div className="shrink-0 mt-1">{meta.icon}</div>
        <div>
          <h3 className="text-lg font-bold">{recommendation.headline}</h3>
          <div className="text-sm opacity-80 mt-1">
            Confidence: {Math.round(recommendation.confidence * 100)}%
          </div>
        </div>
      </div>
      
      <div className="p-5">
        <h4 className="text-sm font-semibold text-slate-700 uppercase tracking-wider mb-3">Key Reasons</h4>
        <ul className="space-y-2 mb-6">
          {recommendation.reasons.map((reason, idx) => (
            <li key={idx} className="flex gap-3 text-slate-700">
              <span className="text-guard-500 font-bold shrink-0">•</span>
              <span>{reason}</span>
            </li>
          ))}
        </ul>

        {recommendation.suggested_actions && recommendation.suggested_actions.length > 0 && (
          <>
            <h4 className="text-sm font-semibold text-slate-700 uppercase tracking-wider mb-3">Suggested Next Steps</h4>
            <ul className="space-y-2">
              {recommendation.suggested_actions.map((action, idx) => (
                <li key={idx} className="flex gap-3 text-slate-600 text-sm bg-slate-50 p-2 rounded border border-slate-100">
                  <svg className="w-5 h-5 text-slate-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                  <span>{action}</span>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}
