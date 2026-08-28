import { AuditEntry } from "../types";

export function AuditHistory({ history }: { history: AuditEntry[] }) {
  if (history.length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 mt-6">
      <h2 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
        <svg className="w-5 h-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Audit History
      </h2>
      
      <div className="relative pl-4 border-l border-slate-200 space-y-6">
        {history.map((entry) => (
          <div key={entry.id} className="relative">
            <div className={`absolute -left-[21px] w-2.5 h-2.5 rounded-full ring-4 ring-white ${
              entry.action === "approve" ? "bg-emerald-500" :
              entry.action === "reject" ? "bg-rose-500" :
              "bg-amber-500"
            }`} />
            
            <div className="flex flex-col sm:flex-row sm:items-baseline justify-between mb-1">
              <h4 className="text-sm font-semibold text-slate-800 capitalize">
                {entry.action.replace(/_/g, " ")}
              </h4>
              <time className="text-xs text-slate-500" dateTime={entry.timestamp}>
                {new Date(entry.timestamp).toLocaleString()}
              </time>
            </div>
            
            <p className="text-xs text-slate-500 mb-2">By {entry.reviewer}</p>
            
            {entry.notes && (
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 text-sm text-slate-700 italic">
                "{entry.notes}"
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
