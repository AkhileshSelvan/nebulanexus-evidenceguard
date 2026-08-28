import { Explanation } from "../types";

export function ExplanationPanel({ explanation }: { explanation: Explanation }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="p-5 border-b border-slate-100 bg-slate-50">
        <h2 className="text-lg font-bold text-slate-800">Explanation</h2>
        <p className="text-sm text-slate-700 mt-2 leading-relaxed">{explanation.summary}</p>
      </div>

      <div className="p-5 space-y-6">
        <div>
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-4">Key Factors</h3>
          <div className="space-y-4">
            {explanation.factors.map((factor, i) => (
              <div key={i} className="flex gap-4">
                <div className="shrink-0 mt-0.5">
                  {factor.impact === "increases_risk" ? (
                    <svg className="w-5 h-5 text-rose-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
                    </svg>
                  ) : factor.impact === "decreases_risk" ? (
                    <svg className="w-5 h-5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14" />
                    </svg>
                  )}
                </div>
                <div>
                  <h4 className="font-semibold text-slate-800 text-sm">
                    {factor.title}
                    <span className="ml-2 px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-500 uppercase">
                      {factor.weight} weight
                    </span>
                  </h4>
                  {factor.evidence.length > 0 && (
                    <ul className="mt-2 space-y-1.5">
                      {factor.evidence.map((ev, idx) => (
                        <li key={idx} className="text-xs text-slate-600 bg-slate-50 p-2 rounded border border-slate-100">
                          <span className="font-medium text-slate-700">{ev.document_id}</span> ({ev.section}): "{ev.quote}"
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {explanation.glossary.length > 0 && (
          <div className="pt-4 border-t border-slate-100">
            <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">Glossary</h3>
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {explanation.glossary.map((entry, i) => (
                <div key={i} className="text-sm">
                  <dt className="font-semibold text-slate-700">{entry.term}</dt>
                  <dd className="text-slate-500 mt-0.5 leading-relaxed">{entry.definition}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </div>
    </div>
  );
}
