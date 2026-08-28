import { useState } from "react";
import { ReportDocumentEntry } from "../types";

export function EvidenceCard({ entry }: { entry: ReportDocumentEntry }) {
  const [activeTab, setActiveTab] = useState<"extraction" | "forensics" | "metadata">("extraction");
  const doc = entry.document;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
        <div className="min-w-0">
          <h3 className="font-semibold text-slate-800 truncate" title={doc.filename}>
            {doc.filename}
          </h3>
          <p className="text-xs text-slate-500 mt-1 capitalize">
            {doc.detected_type?.replace(/_/g, " ") || "Unknown Type"} • {(doc.byte_size / 1024).toFixed(1)} KB
          </p>
        </div>
        <div className={`shrink-0 px-2.5 py-1 rounded text-xs font-bold uppercase ${
          entry.risk.severity === "low" ? "bg-emerald-100 text-emerald-700" :
          entry.risk.severity === "medium" ? "bg-amber-100 text-amber-700" :
          "bg-rose-100 text-rose-700"
        }`}>
          Risk: {Math.round(entry.risk.score)}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 bg-white px-2">
        {(["extraction", "forensics", "metadata"] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-3 text-sm font-medium capitalize border-b-2 transition-colors ${
              activeTab === tab 
                ? "border-guard-500 text-guard-600" 
                : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div className="p-0 overflow-y-auto max-h-80 bg-slate-50/30 flex-1">
        {activeTab === "extraction" && (
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-50 sticky top-0 border-b border-slate-200">
              <tr>
                <th className="px-4 py-2 font-semibold text-slate-600">Field</th>
                <th className="px-4 py-2 font-semibold text-slate-600">Value</th>
                <th className="px-4 py-2 font-semibold text-slate-600 w-16">Conf</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {entry.extraction.fields.map((f, i) => (
                <tr key={i} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-2 text-slate-500 font-medium whitespace-nowrap">{f.key.replace(/_/g, " ")}</td>
                  <td className="px-4 py-2 text-slate-800 font-mono text-xs">{f.value}</td>
                  <td className="px-4 py-2 text-slate-500">
                    <span className={`px-1.5 py-0.5 rounded text-xs ${
                      f.confidence > 0.9 ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"
                    }`}>
                      {Math.round(f.confidence * 100)}%
                    </span>
                  </td>
                </tr>
              ))}
              {entry.extraction.fields.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-4 py-8 text-center text-slate-500 italic">No fields extracted.</td>
                </tr>
              )}
            </tbody>
          </table>
        )}

        {activeTab === "forensics" && (
          <div className="p-4 space-y-4">
            <p className="text-sm text-slate-600 mb-2">{entry.forensics.summary}</p>
            {entry.forensics.signals.map((sig, i) => (
              <div key={i} className={`p-3 border rounded-lg ${sig.passed ? 'bg-emerald-50/50 border-emerald-100' : 'bg-rose-50/50 border-rose-100'}`}>
                <div className="flex justify-between items-start mb-1">
                  <h4 className="font-medium text-slate-800 text-sm">{sig.label}</h4>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${sig.passed ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'}`}>
                    {sig.passed ? 'Pass' : 'Flag'}
                  </span>
                </div>
                <p className="text-xs text-slate-600 mt-1">{sig.detail}</p>
                {sig.regions.length > 0 && (
                  <div className="mt-2 text-xs text-slate-500">
                    {sig.regions.length} annotated region(s)
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {activeTab === "metadata" && (
          <div className="p-4 space-y-4">
            <p className="text-sm text-slate-600 mb-2">{entry.metadata.summary}</p>
            
            <div className="space-y-3">
              {entry.metadata.signals.map((sig, i) => (
                <div key={i} className={`p-3 border rounded-lg ${sig.passed ? 'bg-emerald-50/50 border-emerald-100' : 'bg-rose-50/50 border-rose-100'}`}>
                  <div className="flex justify-between items-start mb-1">
                    <h4 className="font-medium text-slate-800 text-sm">{sig.label}</h4>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${sig.passed ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'}`}>
                      {sig.passed ? 'Pass' : 'Flag'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 mt-1">{sig.detail}</p>
                </div>
              ))}
            </div>

            <div className="mt-6">
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Raw File Properties</h4>
              <div className="bg-slate-800 rounded-lg p-3 overflow-x-auto">
                <pre className="text-[10px] sm:text-xs text-slate-300 font-mono leading-relaxed">
                  {Object.entries(entry.metadata.raw).map(([k, v]) => (
                    <div key={k}><span className="text-slate-500">{k}:</span> <span className="text-emerald-300">{String(v)}</span></div>
                  ))}
                </pre>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
