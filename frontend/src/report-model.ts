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

/**
 * Display-only label overrides.
 *
 * "Modified significantly after creation" reads as an accusation; a document
 * edited after creation is an ordinary fact (re-export, scanner app, page
 * merge) and the score already reflects how much weight it carries. The
 * neutral wording is applied here rather than in the analyzer because the
 * backend owns that label and is out of scope for presentation work.
 */
const LABEL_OVERRIDES: Record<string, string> = {
  "Modified significantly after creation": "Modified after creation",
  "Modified shortly after creation": "Modified after creation",
};

export function displayLabel(label: string): string {
  return LABEL_OVERRIDES[label] ?? label;
}

/**
 * Same overrides, applied inside longer backend prose.
 *
 * Section summaries embed the label ("1 metadata concern(s): Modified
 * significantly after creation."), so an exact-match lookup misses them. This
 * substitutes only the known phrases above — it is not general rewriting of
 * analyzer text, which is always rendered verbatim otherwise.
 */
export function displayText(text: string): string {
  let out = text;
  for (const [from, to] of Object.entries(LABEL_OVERRIDES)) {
    out = out.split(from).join(to);
  }
  return out;
}

/**
 * Materiality threshold for "does a reviewer need to look at this document?".
 *
 * Not an arbitrary number: the risk calibration already encoded which evidence
 * is weak, by capping it. `MISSING_METADATA_ABSENT_SCORE` is 12.0 and
 * `MISSING_METADATA_PARTIAL_CAP` is 10.0, so anything at or below 12 is, by the
 * analyzer's own reckoning, not something to act on alone. Measured on a real
 * bundle of nine legitimate scanned credentials, everything below this line was
 * ELA at 0.1-3.4 (documented as non-discriminating on scanned input) or capped
 * metadata at 3.0-6.0; the two findings above it were the genuine
 * modified-after-creation gaps.
 */
export const MATERIAL_SCORE_THRESHOLD = 12;

/**
 * Signal classes the calibration documented as weak evidence. They stay fully
 * visible in the document's evidence, but on their own they do not make a
 * document "needs review".
 */
const WEAK_SIGNAL_IDS = new Set([
  "missing_expected_metadata",
  "ocr_low_text_confidence",
  "ocr_no_text_extracted",
]);

/** A finding the analyzer recorded but deliberately did not score. */
export function isInformationalSignal(detail: string | undefined): boolean {
  return (detail ?? "").includes("[informational:");
}

/**
 * Is this signal something a reviewer should actually act on?
 *
 * Presentation classification only — it never changes the signal, its score, or
 * the document's risk. It decides placement, nothing else.
 */
export function isMaterialSignal(s: {
  id: string;
  score: number;
  passed: boolean;
  detail?: string;
}): boolean {
  if (s.passed) return false;
  if (isInformationalSignal(s.detail)) return false;
  if (WEAK_SIGNAL_IDS.has(s.id)) return false;
  return s.score > MATERIAL_SCORE_THRESHOLD;
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
  /** Flagged findings that clear the materiality bar — the ones to act on. */
  materialCount: number;
  /** The strongest material finding, for the one-line summary. */
  topIssue: string | null;
  /** Flagged but weak/informational — shown in the document, not promoted. */
  minorCount: number;
  /** Findings recorded but deliberately not scored (e.g. PDF pipeline artifacts). */
  informationalCount: number;
  /** True only when a material finding exists. Placement only. */
  needsAttention: boolean;
}

/**
 * Documents ordered by their own risk score, split by whether they carry a
 * finding a reviewer should act on.
 *
 * Placement only. Every document, and every finding inside it, remains present
 * and reachable — documents without a material finding move behind "View
 * remaining documents" rather than being dropped. Previously any flagged signal
 * at all promoted a document, so nine legitimate scans all read as "need
 * attention" on the strength of noise-floor ELA and capped metadata.
 */
export function summariseDocuments(report: VerificationReport): DocumentSummary[] {
  return report.documents
    .map((entry) => {
      const all = [...entry.forensics.signals, ...entry.metadata.signals];
      const flagged = all.filter((s) => !s.passed).sort((a, b) => b.score - a.score);
      const material = flagged.filter((s) => isMaterialSignal(s));
      const informational = all.filter((s) => isInformationalSignal(s.detail)).length;

      return {
        entry,
        filename: entry.document.filename,
        riskScore: entry.risk.score,
        severity: entry.risk.severity,
        flaggedCount: flagged.length,
        materialCount: material.length,
        topIssue: material.length > 0 ? displayLabel(material[0].label) : null,
        minorCount: flagged.length - material.length,
        informationalCount: informational,
        needsAttention: material.length > 0,
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
