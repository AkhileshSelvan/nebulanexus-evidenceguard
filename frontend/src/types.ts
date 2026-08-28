// ---------------------------------------------------------------------------
// EvidenceGuard — shared TypeScript types matching docs/API_CONTRACT.md v0.1.1
// ---------------------------------------------------------------------------

/** ISO-8601 UTC timestamp string, e.g. "2026-08-28T10:36:00Z" */
export type ISOTimestamp = string;

/** Score value in [0, 100]. 0 = no concern, 100 = maximum concern. */
export type Score = number;

/** Confidence value in [0, 1]. */
export type Confidence = number;

// ── §1 document ────────────────────────────────────────────────────────────

export interface PageInfo {
  page_number: number;
  width: number;
  height: number;
  image_ref: string;
}

export interface DocumentInfo {
  id: string;
  bundle_id: string;
  filename: string;
  media_type: string;
  byte_size: number;
  sha256: string;
  page_count: number;
  declared_type: string | null;
  detected_type: string | null;
  pages: PageInfo[];
  received_at: ISOTimestamp;
}

// ── §2 extraction ──────────────────────────────────────────────────────────

export interface ExtractionField {
  key: string;
  value: string;
  value_normalized: string;
  data_type: "string" | "date" | "number" | "currency" | "id";
  confidence: Confidence;
  page: number;
  bbox: [number, number, number, number] | null;
}

export interface ExtractionPage {
  page_number: number;
  source: "image" | "pdf";
  width: number;
  height: number;
  rotation_applied: number;
  text_confidence: Confidence;
  char_count: number;
}

export interface Extraction {
  engine: string;
  engine_version: string;
  language: string;
  full_text: string;
  text_confidence: Confidence;
  fields: ExtractionField[];
  tables: unknown[];
  warnings: string[];
  pages: ExtractionPage[];
}

// ── §3 forensics ───────────────────────────────────────────────────────────

export interface ForensicRegion {
  page: number;
  bbox: [number, number, number, number];
  note: string;
}

export interface ForensicSignal {
  id: string;
  label: string;
  score: Score;
  confidence: Confidence;
  passed: boolean;
  pages: number[];
  regions: ForensicRegion[];
  detail: string;
}

export interface ForensicsResult {
  engine: string;
  engine_version: string;
  signals: ForensicSignal[];
  score: Score;
  summary: string;
}

// ── §4 metadata ────────────────────────────────────────────────────────────

export interface MetadataSignal {
  id: string;
  label: string;
  score: Score;
  confidence: Confidence;
  passed: boolean;
  detail: string;
}

export interface MetadataDerived {
  created_at: ISOTimestamp | null;
  modified_at: ISOTimestamp | null;
  producer: string | null;
  creator_tool: string | null;
  has_gps: boolean;
  software_edits: string[];
}

export interface MetadataResult {
  engine: string;
  engine_version: string;
  container: string;
  raw: Record<string, string>;
  derived: MetadataDerived;
  signals: MetadataSignal[];
  score: Score;
  summary: string;
}

// ── §5 consistency ─────────────────────────────────────────────────────────

export interface ConsistencyObserved {
  document_id: string;
  value: string;
}

export interface ConsistencyCheck {
  id: string;
  label: string;
  field: string;
  status: "pass" | "warn" | "fail" | "not_applicable";
  score: Score;
  confidence: Confidence;
  observed: ConsistencyObserved[];
  detail: string;
}

export interface ConsistencyCrossRef {
  check_id: string;
  document_ids: string[];
}

export interface ConsistencyResult {
  engine: string;
  engine_version: string;
  checks: ConsistencyCheck[];
  cross_references: ConsistencyCrossRef[];
  score: Score;
  summary: string;
}

// ── §6 risk ────────────────────────────────────────────────────────────────

export type Severity = "low" | "medium" | "high" | "critical";

export interface RiskContribution {
  source: "ocr" | "forensics" | "metadata" | "consistency";
  signal_id: string;
  signal_score: Score;
  weight: number;
  contribution: number;
}

export interface RiskResult {
  engine: string;
  engine_version: string;
  scope: "document" | "bundle";
  subject_id: string;
  score: Score;
  severity: Severity;
  contributions: RiskContribution[];
  model: {
    method: string;
    version: string;
  };
}

// ── §7 recommendation ──────────────────────────────────────────────────────

export type Decision = "accept" | "review" | "reject";

export interface Recommendation {
  decision: Decision;
  confidence: Confidence;
  headline: string;
  reasons: string[];
  suggested_actions: string[];
  based_on: {
    bundle_risk_score: Score;
    severity: Severity;
  };
}

// ── §8 explanation ─────────────────────────────────────────────────────────

export interface EvidencePointer {
  document_id: string;
  section: "extraction" | "forensics" | "metadata" | "consistency";
  signal_id: string;
  quote: string;
  page: number | null;
  bbox: [number, number, number, number] | null;
}

export interface ExplanationFactor {
  title: string;
  impact: "increases_risk" | "decreases_risk" | "neutral";
  weight: "minor" | "moderate" | "major";
  evidence: EvidencePointer[];
}

export interface GlossaryEntry {
  term: string;
  definition: string;
}

export interface Explanation {
  summary: string;
  factors: ExplanationFactor[];
  glossary: GlossaryEntry[];
}

// ── §9 module error ────────────────────────────────────────────────────────

export interface ModuleError {
  module: "ocr" | "forensics" | "consistency" | "risk" | "ingest";
  scope: "document" | "bundle";
  subject_id: string;
  kind: "timeout" | "exception" | "unsupported_media" | "bad_input";
  message: string;
  at: ISOTimestamp;
}

// ── §0 top-level report ────────────────────────────────────────────────────

export interface DocumentEntry {
  document: DocumentInfo;
  extraction: Extraction;
  forensics: ForensicsResult;
  metadata: MetadataResult;
  risk: RiskResult;
}

export interface BundleInfo {
  bundle_id: string;
  document_count: number;
}

export type ReportStatus = "complete" | "partial" | "failed";

export interface VerificationReport {
  report_id: string;
  created_at: ISOTimestamp;
  status: ReportStatus;
  bundle: BundleInfo;
  documents: DocumentEntry[];
  consistency: ConsistencyResult;
  risk: RiskResult;
  recommendation: Recommendation;
  explanation: Explanation;
  errors: ModuleError[];
}

// ── Reviewer audit (frontend-only) ─────────────────────────────────────────

export interface AuditEntry {
  id: string;
  action: "approve" | "reject" | "request_more_evidence";
  reviewer: string;
  notes: string;
  timestamp: ISOTimestamp;
}
