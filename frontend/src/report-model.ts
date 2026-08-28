/**
 * Presentation model for a VerificationReport.
 *
 * PURE SELECTION ONLY. Every function here reads the report and re-orders,
 * groups or labels what is already in it. Nothing recomputes a score, changes a
 * severity, alters a recommendation, or drops a finding from the data — the
 * full report object stays intact and every signal remains reachable through
 * the detail views. This file exists so that claim is easy to audit in one
 * place instead of being spread through JSX.
 */

import type {
  Consistency,
  ConsistencyCheck,
  ReportDocumentEntry,
  RiskContribution,
  VerificationReport,
} from "./types";

/** Split "<signal_id>@<document_id>" from the RIGHT (a module's own id may contain "@"). */
export function splitSignalId(raw: string): { signalId: string; documentId: string | null } {
  const at = raw.lastIndexOf("@");
  if (at === -1) return { signalId: raw, documentId: null };
  return { signalId: raw.slice(0, at), documentId: raw.slice(at + 1) || null };
}

/** "ela_hotspot" -> "Ela hotspot" — only used when no module label exists. */
function humanise(id: string): string {
  const s = id.replace(/_/g, " ").trim();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

const SOURCE_LABEL: Record<RiskContribution["source"], string> = {
  ocr: "Document text",
  forensics: "Image forensics",
  metadata: "File metadata",
  consistency: "Cross-document",
};

export interface Reason {
  /** What happened — the producing module's own label where one exists. */
  what: string;
  /** Which document — filename, or null for a bundle-wide finding. */
  where: string | null;
  /** Why it matters — the producing module's own detail/quote, verbatim. */
  why: string;
  points: number;
  source: RiskContribution["source"];
  sourceLabel: string;
  /** Kept for the technical detail views. */
  signalId: string;
  documentId: string | null;
  signalScore: number;
}

/**
 * The reasons behind the score, strongest first.
 *
 * Ordering comes straight from `risk.contributions` (already sorted by the
 * backend's own attribution). We only attach the human label and detail text
 * that the producing module already wrote.
 */
export function buildReasons(report: VerificationReport): Reason[] {
  const filenameById = new Map(report.documents.map((d) => [d.document.id, d.document.filename]));

  const findDetail = (
    source: RiskContribution["source"],
    signalId: string,
    documentId: string | null,
  ): { label: string; detail: string } => {
    if (source === "consistency") {
      const c = report.consistency.checks.find((x) => x.id === signalId);
      if (c) return { label: c.label, detail: c.detail };
    }
    const entry = documentId
      ? report.documents.find((d) => d.document.id === documentId)
      : undefined;
    if (entry) {
      if (source === "forensics") {
        const s = entry.forensics.signals.find((x) => x.id === signalId);
        if (s) return { label: s.label, detail: s.detail };
      }
      if (source === "metadata") {
        const s = entry.metadata.signals.find((x) => x.id === signalId);
        if (s) return { label: s.label, detail: s.detail };
      }
      if (source === "ocr") {
        const w = entry.extraction.warnings?.find((x) => x.includes(signalId.replace(/_/g, " ")));
        if (w) return { label: humanise(signalId), detail: w };
      }
    }
    // Fall back to the explanation's own evidence quote when the section text
    // is not reachable (never invent wording).
    for (const factor of report.explanation.factors) {
      const ev = factor.evidence.find((e) => e.signal_id === signalId);
      if (ev) return { label: factor.title, detail: ev.quote };
    }
    return { label: humanise(signalId), detail: "" };
  };

  return report.risk.contributions.map((c) => {
    const { signalId, documentId } = splitSignalId(c.signal_id);
    const { label, detail } = findDetail(c.source, signalId, documentId);
    return {
      what: label,
      where: documentId ? filenameById.get(documentId) ?? null : null,
      why: detail,
      points: c.contribution,
      source: c.source,
      sourceLabel: SOURCE_LABEL[c.source],
      signalId,
      documentId,
      signalScore: c.signal_score,
    };
  });
}

export interface DocumentSummary {
  entry: ReportDocumentEntry;
  filename: string;
  riskScore: number;
  severity: ReportDocumentEntry["risk"]["severity"];
  /** Signals the producing module flagged (passed === false). */
  flaggedCount: number;
  /** The strongest flagged finding, for the one-line summary. */
  topIssue: string | null;
  /** Findings recorded but deliberately not scored (e.g. PDF pipeline artifacts). */
  informationalCount: number;
  needsAttention: boolean;
}

/**
 * Documents ordered by their own risk score, with a one-line "most important
 * issue". `needsAttention` marks the ones worth showing first; the rest stay
 * available behind "View all documents" — nothing is removed.
 */
export function summariseDocuments(report: VerificationReport): DocumentSummary[] {
  return report.documents
    .map((entry) => {
      const flagged = [
        ...entry.forensics.signals.filter((s) => !s.passed),
        ...entry.metadata.signals.filter((s) => !s.passed),
      ].sort((a, b) => b.score - a.score);

      const informational = [...entry.forensics.signals, ...entry.metadata.signals].filter(
        (s) => (s.detail ?? "").includes("[informational:"),
      ).length;

      return {
        entry,
        filename: entry.document.filename,
        riskScore: entry.risk.score,
        severity: entry.risk.severity,
        flaggedCount: flagged.length,
        topIssue: flagged.length > 0 ? flagged[0].label : null,
        informationalCount: informational,
        needsAttention: flagged.length > 0 || entry.risk.score > 0,
      };
    })
    .sort((a, b) => b.riskScore - a.riskScore);
}

export interface ConsistencyTally {
  total: number;
  pass: number;
  warn: number;
  fail: number;
  notApplicable: number;
  /** fail + warn, strongest first — the checks a reviewer actually acts on. */
  actionable: ConsistencyCheck[];
  /** Everything else, kept for the expanded view. */
  rest: ConsistencyCheck[];
}

export function tallyConsistency(consistency: Consistency): ConsistencyTally {
  const checks = consistency.checks ?? [];
  const by = (s: ConsistencyCheck["status"]) => checks.filter((c) => c.status === s);
  const actionable = [...by("fail"), ...by("warn")].sort((a, b) => b.score - a.score);
  const actionableIds = new Set(actionable.map((c) => c.id));
  return {
    total: checks.length,
    pass: by("pass").length,
    warn: by("warn").length,
    fail: by("fail").length,
    notApplicable: by("not_applicable").length,
    actionable,
    rest: checks.filter((c) => !actionableIds.has(c.id)),
  };
}

/** Compact one-line health string for the audit summary. */
export function pluralise(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`;
}
