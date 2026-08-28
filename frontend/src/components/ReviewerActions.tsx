import { useState } from "react";
import { AuditEntry } from "../types";

interface ReviewerActionsProps {
  onAction: (action: AuditEntry["action"], notes: string) => void;
}

export function ReviewerActions({ onAction }: ReviewerActionsProps) {
  const [notes, setNotes] = useState("");
  const [showRejectConfirm, setShowRejectConfirm] = useState(false);

  const handleAction = (action: AuditEntry["action"]) => {
    if (action === "reject" && !showRejectConfirm) {
      setShowRejectConfirm(true);
      return;
    }
    onAction(action, notes);
    setNotes("");
    setShowRejectConfirm(false);
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
      <h2 className="text-lg font-bold text-slate-800 mb-4">Reviewer Decision</h2>
      
      <div className="mb-5">
        <label htmlFor="reviewer-notes" className="block text-sm font-medium text-slate-700 mb-2">
          Internal Notes (Optional)
        </label>
        <textarea
          id="reviewer-notes"
          rows={3}
          className="w-full rounded-md border-slate-300 shadow-sm focus:border-guard-500 focus:ring-guard-500 sm:text-sm border p-3 bg-slate-50 placeholder-slate-400"
          placeholder="Add any notes about this decision..."
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </div>

      {showRejectConfirm ? (
        <div className="bg-rose-50 border border-rose-200 rounded-lg p-4 mb-4 animate-fade-in">
          <h3 className="text-sm font-semibold text-rose-800 mb-1">Confirm Rejection</h3>
          <p className="text-sm text-rose-600 mb-4">Are you sure you want to reject this bundle? This action cannot be undone.</p>
          <div className="flex gap-3">
            <button
              onClick={() => handleAction("reject")}
              className="px-4 py-2 bg-rose-600 text-white text-sm font-medium rounded-md hover:bg-rose-700 shadow-sm"
            >
              Yes, Reject Bundle
            </button>
            <button
              onClick={() => setShowRejectConfirm(false)}
              className="px-4 py-2 bg-white text-slate-700 border border-slate-300 text-sm font-medium rounded-md hover:bg-slate-50"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="flex flex-col sm:flex-row gap-3">
          <button
            onClick={() => handleAction("approve")}
            className="flex-1 flex justify-center items-center gap-2 px-4 py-2.5 bg-emerald-600 text-white font-medium rounded-lg hover:bg-emerald-700 shadow-sm transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Approve
          </button>
          
          <button
            onClick={() => handleAction("request_more_evidence")}
            className="flex-1 flex justify-center items-center gap-2 px-4 py-2.5 bg-amber-500 text-white font-medium rounded-lg hover:bg-amber-600 shadow-sm transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            Request Evidence
          </button>
          
          <button
            onClick={() => handleAction("reject")}
            className="flex-1 flex justify-center items-center gap-2 px-4 py-2.5 bg-white border border-rose-200 text-rose-600 font-medium rounded-lg hover:bg-rose-50 shadow-sm transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
            Reject
          </button>
        </div>
      )}
    </div>
  );
}
