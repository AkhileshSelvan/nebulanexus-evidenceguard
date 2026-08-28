import { Consistency } from "../types";

export function ConsistencyPanel({ consistency }: { consistency: Consistency }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="p-5 border-b border-slate-100">
        <h2 className="text-lg font-bold text-slate-800">Cross-Document Consistency</h2>
        <p className="text-sm text-slate-500 mt-1">{consistency.summary}</p>
      </div>

      <div className="divide-y divide-slate-100">
        {consistency.checks.map((check, i) => (
          <div key={i} className="p-5 hover:bg-slate-50 transition-colors">
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="font-semibold text-slate-800">{check.label}</h3>
                <p className="text-sm text-slate-500 mt-0.5">{check.detail}</p>
              </div>
              <span className={`px-2.5 py-1 rounded text-xs font-bold uppercase shrink-0 ml-4 ${
                check.status === "pass" ? "bg-emerald-100 text-emerald-700" :
                check.status === "warn" ? "bg-amber-100 text-amber-700" :
                check.status === "fail" ? "bg-rose-100 text-rose-700" :
                "bg-slate-100 text-slate-600"
              }`}>
                {check.status}
              </span>
            </div>

            <div className="mt-4 bg-white border border-slate-200 rounded-lg overflow-hidden">
              <table className="w-full text-sm text-left">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-2 font-semibold text-slate-600 w-1/3">Document</th>
                    <th className="px-4 py-2 font-semibold text-slate-600">Observed Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {check.observed.map((obs, idx) => (
                    <tr key={idx} className="bg-white">
                      <td className="px-4 py-2.5 text-slate-500 font-mono text-xs">{obs.document_id}</td>
                      <td className="px-4 py-2.5 text-slate-800 font-mono text-xs break-all">{obs.value}</td>
                    </tr>
                  ))}
                  {check.observed.length === 0 && (
                    <tr>
                      <td colSpan={2} className="px-4 py-3 text-center text-slate-500 italic">No values observed for comparison.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
