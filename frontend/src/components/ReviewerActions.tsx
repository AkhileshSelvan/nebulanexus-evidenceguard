import { useState } from "react";
import { postDecision } from "../api";
import type { ReviewDecision } from "../types";

interface ReviewerActionsProps {
  reportId: string;
  /** Called after a decision is successfully persisted, so the parent can refresh the audit trail. */
  onDecisionRecorded: () => void;
}

const DECISION_META: Record<ReviewDecision, { label: string; confirm?: string }> = {
  accept: { label: "Accept" },
  review: { label: "Request Evidence" },
  reject: { label: "Reject", confirm: "Are you sure you want to reject this bundle? This action cannot be undone." },
};

export function ReviewerActions({ reportId, onDecisionRecorded }: ReviewerActionsProps) {
  const [reviewerName, setReviewerName] = useState("");
  const [notes, setNotes] = useState("");
  const [pendingConfirm, setPendingConfirm] = useState<ReviewDecision | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recorded, setRecorded] = useState<{ decision: ReviewDecision; reviewerName: string; notes: string; reviewedAt: string } | null>(null);

  const submit = async (decision: ReviewDecision) => {
    if (!reviewerName.trim()) {
      setError("Enter your name before recording a decision.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const result = await postDecision(reportId, {
        decision,
        reviewer_name: reviewerName.trim(),
        notes: notes.trim() || undefined,
      });
      setRecorded({
        decision: result.reviewer_decision,
        reviewerName: result.reviewer_name,
        notes: result.reviewer_notes ?? "",
        reviewedAt: result.reviewed_at,
      });
      setNotes("");
      setPendingConfirm(null);
      onDecisionRecorded();
    } catch (err) {
      // Honest failure: never invent a "recorded" state on a request that
      // didn't actually reach the backend.
      setError(err instanceof Error ? err.message : "Could not record this decision.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleClick = (decision: ReviewDecision) => {
    const meta = DECISION_META[decision];
    if (meta.confirm && pendingConfirm !== decision) {
      setPendingConfirm(decision);
      return;
    }
    void submit(decision);
  };

  if (recorded) {
    return (
      <div className="eg-card p-5">
        <h2 className="text-base font-bold text-slate-900 mb-3">Reviewer decision</h2>
        <div className={`p-3 rounded-lg border text-sm ${
          recorded.decision === "accept" ? "bg-emerald-50 border-emerald-200 text-emerald-800" :
          recorded.decision === "reject" ? "bg-rose-50 border-rose-200 text-rose-800" :
          "bg-amber-50 border-amber-200 text-amber-800"
        }`}>
          <p className="font-semibold capitalize">{recorded.decision}</p>
          <p className="mt-1 text-xs opacity-80">By {recorded.reviewerName} &middot; {new Date(recorded.reviewedAt).toLocaleString()}</p>
          {recorded.notes && <p className="mt-2 italic">&quot;{recorded.notes}&quot;</p>}
        </div>
        <button
          onClick={() => setRecorded(null)}
          className="mt-3 text-sm font-medium text-guard-600 hover:text-guard-700"
        >
          Change decision
        </button>
      </div>
    );
  }

  return (
    <div className="eg-card p-5">
      <h2 className="text-base font-bold text-slate-900 mb-4">Reviewer decision</h2>

      <div className="mb-4">
        <label htmlFor="reviewer-name" className="block text-sm font-medium text-slate-700 mb-2">
          Your name
        </label>
        <input
          id="reviewer-name"
          type="text"
          className="w-full rounded-md border-slate-300 shadow-sm focus:border-guard-500 focus:ring-guard-500 sm:text-sm border p-2.5 bg-slate-50 placeholder-slate-400"
          placeholder="e.g. Priya R"
          value={reviewerName}
          onChange={(e) => setReviewerName(e.target.value)}
          disabled={submitting}
        />
      </div>

      <div className="mb-5">
        <label htmlFor="reviewer-notes" className="block text-sm font-medium text-slate-700 mb-2">
          Internal notes (optional)
        </label>
        <textarea
          id="reviewer-notes"
          rows={3}
          className="w-full rounded-md border-slate-300 shadow-sm focus:border-guard-500 focus:ring-guard-500 sm:text-sm border p-3 bg-slate-50 placeholder-slate-400"
          placeholder="Add any notes about this decision..."
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          disabled={submitting}
        />
      </div>

      {error && (
        <p className="eg-scale-in mb-4 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert">{error}</p>
      )}

      {pendingConfirm === "reject" ? (
        <div className="eg-scale-in mb-4 rounded-lg border border-rose-200 bg-rose-50 p-4">
          <h3 className="text-sm font-semibold text-rose-800 mb-1">Confirm rejection</h3>
          <p className="text-sm text-rose-600 mb-4">{DECISION_META.reject.confirm}</p>
          <div className="flex gap-3">
            <button
              onClick={() => handleClick("reject")}
              disabled={submitting}
              className="eg-press min-h-[44px] rounded-lg bg-rose-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-rose-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? "Recording…" : "Yes, reject bundle"}
            </button>
            <button
              onClick={() => setPendingConfirm(null)}
              disabled={submitting}
              className="eg-press min-h-[44px] rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="flex flex-col sm:flex-row gap-3">
          <button
            onClick={() => handleClick("accept")}
            disabled={submitting}
            className="eg-press flex min-h-[44px] flex-1 items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? "Recording…" : "Accept"}
          </button>

          <button
            onClick={() => handleClick("review")}
            disabled={submitting}
            className="eg-press flex min-h-[44px] flex-1 items-center justify-center gap-2 rounded-lg bg-amber-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-amber-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? "Recording…" : "Request evidence"}
          </button>

          <button
            onClick={() => handleClick("reject")}
            disabled={submitting}
            className="eg-press flex min-h-[44px] flex-1 items-center justify-center gap-2 rounded-lg border border-rose-300 bg-white px-4 py-2.5 text-sm font-semibold text-rose-700 shadow-sm hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Reject
          </button>
        </div>
      )}
    </div>
  );
}
