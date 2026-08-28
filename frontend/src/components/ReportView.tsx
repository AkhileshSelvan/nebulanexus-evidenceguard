import { useState } from "react";
import { VerificationReport, AuditEntry } from "../types";
import { RiskBanner } from "./RiskBanner";
import { RecommendationCard } from "./RecommendationCard";
import { EvidenceCard } from "./EvidenceCard";
import { ConsistencyPanel } from "./ConsistencyPanel";
import { ExplanationPanel } from "./ExplanationPanel";
import { ReviewerActions } from "./ReviewerActions";
import { AuditHistory } from "./AuditHistory";

export function ReportView({ report, onReset }: { report: VerificationReport; onReset: () => void }) {
  const [auditLog, setAuditLog] = useState<AuditEntry[]>([]);

  const handleReviewerAction = (action: AuditEntry["action"], notes: string) => {
    const newEntry: AuditEntry = {
      id: crypto.randomUUID(),
      action,
      notes,
      reviewer: "Current User",
      timestamp: new Date().toISOString(),
    };
    setAuditLog([newEntry, ...auditLog]);
  };

  return (
    <div className="max-w-6xl mx-auto w-full pb-20 animate-fade-in space-y-6">
      <div className="flex justify-between items-center bg-white p-4 rounded-xl shadow-sm border border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-800">Bundle Verification Report</h1>
          <p className="text-sm text-slate-500 mt-1">
            ID: <span className="font-mono">{report.bundle.bundle_id}</span> • {report.bundle.document_count} documents
          </p>
        </div>
        <button
          onClick={onReset}
          className="px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
        >
          New Verification
        </button>
      </div>

      <RiskBanner risk={report.risk} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <ExplanationPanel explanation={report.explanation} />
          <ConsistencyPanel consistency={report.consistency} />

          <section>
            <h2 className="text-lg font-bold text-slate-800 mb-4 px-1">Document Evidence</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {report.documents.map((doc, idx) => (
                <EvidenceCard key={idx} entry={doc} />
              ))}
            </div>
          </section>
        </div>

        <div className="space-y-6">
          <RecommendationCard recommendation={report.recommendation} />
          <ReviewerActions onAction={handleReviewerAction} />
          <AuditHistory history={auditLog} />
        </div>
      </div>
    </div>
  );
}
