// TypeScript mirror of docs/API_CONTRACT.md, kept in lockstep the same way
// modules/contract.py is the Python mirror — a contract change here should
// break the compiler, not prod. Do not hand-shape API responses elsewhere;
// import from here.

export type Severity = "low" | "medium" | "high" | "critical";
export type ReviewDecision = "accept" | "review" | "reject";
export type CheckStatus = "pass" | "warn" | "fail" | "not_applicable";

// --------------------------------------------------------------------- //
// §1 document
// --------------------------------------------------------------------- //

export interface DocumentPage {
  page_number: number;
  width: number;
  height: number;
  image_ref: string;
}

export interface EgDocument {
  id: string;
  bundle_id: string;
  filename: string;
  media_type: string;
  byte_size: number;
  sha256: string;
  page_count: number;
  declared_type: string | null;
  detected_type: string | null;
  pages: DocumentPage[];
  received_at: string;
}

// --------------------------------------------------------------------- //
// §2 extraction — modules/ocr
// --------------------------------------------------------------------- //

export interface ExtractionField {
  key: string;
  value: string | null;
  value_normalized: string | null;
  data_type: "string" | "date" | "number" | "currency" | "id";
  confidence: number;
  page: number | null;
  bbox: [number, number, number, number] | null;
}

export interface ExtractionTable {
  name: string;
  page: number | null;
  columns: string[];
  rows: string[][];
}

export interface ExtractionPageInfo {
  page_number: number;
  source: "image" | "pdf";
  width: number;
  height: number;
  rotation_applied: number;
  text_confidence: number;
  char_count: number;
}

export interface Extraction {
  engine: string;
  engine_version: string;
  language: string | null;
  full_text: string;
  text_confidence: number;
  fields: ExtractionField[];
  tables: ExtractionTable[];
  warnings: string[];
  pages: ExtractionPageInfo[];
}

// --------------------------------------------------------------------- //
// §3 forensics / §4 metadata — modules/forensics
// --------------------------------------------------------------------- //

export interface ForensicRegion {
  page: number;
  bbox: [number, number, number, number];
  note: string | null;
}

export interface ForensicSignal {
  id: string;
  label: string;
  score: number;
  confidence: number;
  passed: boolean;
  pages: number[];
  regions: ForensicRegion[];
  detail: string;
}

export interface Forensics {
  engine: string;
  engine_version: string;
  signals: ForensicSignal[];
  score: number;
  summary: string;
}

export interface MetadataSignal {
  id: string;
  label: string;
  score: number;
  confidence: number;
  passed: boolean;
  detail: string;
}

export interface Metadata {
  engine: string;
  engine_version: string;
  container: string;
  raw: Record<string, unknown>;
  derived: {
    created_at: string | null;
    modified_at: string | null;
    producer: string | null;
    creator_tool: string | null;
    has_gps: boolean;
    software_edits: string[];
  };
  signals: MetadataSignal[];
  score: number;
  summary: string;
}

// --------------------------------------------------------------------- //
// §5 consistency — modules/consistency
// --------------------------------------------------------------------- //

export interface ConsistencyObservation {
  document_id: string;
  value: string | null;
}

export interface ConsistencyCheck {
  id: string;
  label: string;
  field: string | null;
  status: CheckStatus;
  score: number;
  confidence: number;
  observed: ConsistencyObservation[];
  detail: string;
}

export interface ConsistencyCrossRef {
  check_id: string;
  document_ids: string[];
}

export interface Consistency {
  engine: string;
  engine_version: string;
  checks: ConsistencyCheck[];
  cross_references: ConsistencyCrossRef[];
  score: number;
  summary: string;
}

// --------------------------------------------------------------------- //
// §6 risk / §7 recommendation / §8 explanation — modules/risk
// --------------------------------------------------------------------- //

export interface RiskContribution {
  source: "ocr" | "forensics" | "metadata" | "consistency";
  // "<signal_id>@<document_id>" when scope === "bundle" and the signal came
  // from one document; split from the RIGHT (the last "@") since a
  // producing module's own id may itself contain "@".
  signal_id: string;
  signal_score: number;
  weight: number;
  contribution: number;
}

export interface Risk {
  engine: string;
  engine_version: string;
  scope: "document" | "bundle";
  subject_id: string;
  score: number;
  severity: Severity;
  contributions: RiskContribution[];
  model: { method: string; version: string };
}

export interface Recommendation {
  decision: ReviewDecision;
  confidence: number;
  headline: string;
  reasons: string[];
  suggested_actions: string[];
  based_on: { bundle_risk_score: number; severity: Severity };
}

export interface ExplanationEvidence {
  document_id: string;
  section: string;
  signal_id: string;
  quote: string;
  page: number | null;
  bbox: [number, number, number, number] | null;
}

export interface ExplanationFactor {
  title: string;
  impact: "increases_risk" | "decreases_risk" | "neutral";
  weight: "minor" | "moderate" | "major";
  evidence: ExplanationEvidence[];
}

export interface Explanation {
  summary: string;
  factors: ExplanationFactor[];
  glossary: { term: string; definition: string }[];
}

// --------------------------------------------------------------------- //
// §9 ModuleError / §0 VerificationReport
// --------------------------------------------------------------------- //

export interface ModuleError {
  module: "ocr" | "forensics" | "consistency" | "risk" | "ingest";
  scope: "document" | "bundle";
  subject_id: string;
  kind: "timeout" | "exception" | "unsupported_media" | "bad_input";
  message: string;
  at: string;
}

export interface ReportDocumentEntry {
  document: EgDocument;
  extraction: Extraction;
  forensics: Forensics;
  metadata: Metadata;
  risk: Risk;
}

export interface VerificationReport {
  report_id: string;
  created_at: string;
  status: "complete" | "partial" | "failed";
  bundle: { bundle_id: string; document_count: number };
  documents: ReportDocumentEntry[];
  consistency: Consistency;
  risk: Risk;
  recommendation: Recommendation;
  explanation: Explanation;
  errors: ModuleError[];
}

// --------------------------------------------------------------------- //
// §12 case storage, reviewer decisions & audit trail — backend
// --------------------------------------------------------------------- //

export interface CaseSummary {
  report_id: string;
  bundle_id: string;
  created_at: string;
  status: "complete" | "partial" | "failed";
  document_count: number;
  risk_score: number;
  risk_severity: Severity;
  recommendation_decision: ReviewDecision;
  reviewer_decision: ReviewDecision | null;
  reviewer_name: string | null;
  reviewer_notes: string | null;
  reviewed_at: string | null;
}

export interface CaseDetail {
  report: VerificationReport;
  reviewer_decision: ReviewDecision | null;
  reviewer_name: string | null;
  reviewer_notes: string | null;
  reviewed_at: string | null;
}

export interface DecisionRequest {
  decision: ReviewDecision;
  reviewer_name: string;
  notes?: string;
}

export interface DecisionResult {
  report_id: string;
  reviewer_decision: ReviewDecision;
  reviewer_name: string;
  reviewer_notes: string | null;
  reviewed_at: string;
}

export interface AuditEvent {
  id: string;
  report_id: string;
  event_type: "report_created" | "decision_recorded";
  actor: string | null;
  detail: Record<string, unknown>;
  at: string;
}
