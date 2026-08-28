import { useState } from "react";
import type { VerificationReport } from "../types";
import { RiskBanner } from "./RiskBanner";
import { RecommendationCard } from "./RecommendationCard";
import { EvidenceCard } from "./EvidenceCard";
import { ConsistencyPanel } from "./ConsistencyPanel";
import { ExplanationPanel } from "./ExplanationPanel";
import { ReviewerActions } from "./ReviewerActions";
import { AuditHistory } from "./AuditHistory";

export function ReportView({ report, onReset }: { report: VerificationReport; onReset: () => void }) {
  // Bumped after a decision is recorded so <AuditHistory> refetches the real
  // trail from the backend -- there is no client-side audit log anymore.
  const [auditRefreshToken, setAuditRefreshToken] = useState(0);

  return (
    <div className="max-w-6xl mx-auto w-full pb-20 animate-fade-in space-y-6">
      <div className="flex justify-between items-center bg-white p-4 rounded-xl shadow-sm border border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-800">Bundle verification report</h1>
          <p className="text-sm text-slate-500 mt-1">
            ID: <span className="font-mono">{report.bundle.bundle_id}</span> &middot; {report.bundle.document_count} documents
          </p>
        </div>
        <button
          onClick={onReset}
          className="px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
        >
          New verification
        </button>
      </div>

      <RiskBanner risk={report.risk} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <ExplanationPanel explanation={report.explanation} />
          <ConsistencyPanel consistency={report.consistency} />

          <section>
            <h2 className="text-lg font-bold text-slate-800 mb-4 px-1">Document evidence</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {report.documents.map((doc, idx) => (
                <EvidenceCard key={idx} entry={doc} />
              ))}
            </div>
          </section>
        </div>

        <div className="space-y-6">
          <RecommendationCard recommendation={report.recommendation} />
          <ReviewerActions
            reportId={report.report_id}
            onDecisionRecorded={() => setAuditRefreshToken((n) => n + 1)}
          />
          <AuditHistory reportId={report.report_id} refreshToken={auditRefreshToken} />
        </div>
      </div>
    </div>
  );
}
