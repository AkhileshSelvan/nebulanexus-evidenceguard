"""Shared type definitions for the EvidenceGuard JSON contract.

This is the Python mirror of ``docs/API_CONTRACT.md``. Every module imports the
shapes it produces/consumes from here so that a contract change is caught by
type-checking rather than in a demo.

Nothing in this file does any work — it is types + two tiny helpers only.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

# --------------------------------------------------------------------------- #
# Severity bands (see API_CONTRACT.md §6). Shared by the risk module, the      #
# backend, the frontend (mirrored in TS), and tests.                          #
# --------------------------------------------------------------------------- #

Severity = Literal["low", "medium", "high", "critical"]

# (inclusive lower bound, inclusive upper bound)
SEVERITY_BANDS: dict[Severity, tuple[int, int]] = {
    "low": (0, 24),
    "medium": (25, 49),
    "high": (50, 74),
    "critical": (75, 100),
}

# severity -> default reviewer decision (the risk module may override w/ a reason)
DEFAULT_DECISION_FOR_SEVERITY: dict[Severity, Literal["accept", "review", "reject"]] = {
    "low": "accept",
    "medium": "review",
    "high": "review",
    "critical": "reject",
}


def severity_for_score(score: float) -> Severity:
    """Map a 0–100 risk score onto its severity band."""
    clamped = max(0.0, min(100.0, float(score)))
    for band, (low, high) in SEVERITY_BANDS.items():
        if low <= clamped <= high:
            return band
    return "critical"  # unreachable given the bands above, kept for type-safety


# --------------------------------------------------------------------------- #
# §1  document                                                                #
# --------------------------------------------------------------------------- #


class DocumentPage(TypedDict):
    page_number: int
    width: int
    height: int
    image_ref: str


class Document(TypedDict):
    id: str
    bundle_id: str
    filename: str
    media_type: str
    byte_size: int
    sha256: str
    page_count: int
    declared_type: str | None
    detected_type: str | None
    pages: list[DocumentPage]
    received_at: str


# --------------------------------------------------------------------------- #
# §2  extraction  (modules/ocr)                                               #
# --------------------------------------------------------------------------- #


class ExtractionField(TypedDict):
    key: str
    value: str | None
    value_normalized: str | None
    data_type: Literal["string", "date", "number", "currency", "id"]
    confidence: float
    page: int | None
    bbox: list[float] | None


class ExtractionTable(TypedDict):
    name: str
    page: int | None
    columns: list[str]
    rows: list[list[str]]


class ExtractionPageInfo(TypedDict):
    page_number: int          # 1-based
    source: str               # "image" | "pdf"
    width: int                # px of the processed raster
    height: int               # px of the processed raster
    rotation_applied: int     # degrees the preprocessor rotated the page (0/90/180/270)
    text_confidence: float    # [0,1] mean OCR word confidence for this page, 0.0 if none
    char_count: int           # length of this page's OCR text


class Extraction(TypedDict):
    engine: str
    engine_version: str
    language: str | None
    full_text: str
    text_confidence: float
    fields: list[ExtractionField]
    tables: list[ExtractionTable]
    # Non-fatal notes: OCR engine missing, low confidence, undecodable page, etc.
    # Consumers that ignore this key are unaffected (additive, v0.1.1).
    warnings: list[str]
    # Per-source raster info, one entry per page actually processed. May be [].
    pages: list["ExtractionPageInfo"]


# --------------------------------------------------------------------------- #
# §3  forensics  (modules/forensics)                                          #
# --------------------------------------------------------------------------- #


class ForensicRegion(TypedDict):
    page: int
    bbox: list[float]
    note: str | None


class ForensicSignal(TypedDict):
    id: str
    label: str
    score: float
    confidence: float
    passed: bool
    pages: list[int]
    regions: list[ForensicRegion]
    detail: str


class Forensics(TypedDict):
    engine: str
    engine_version: str
    signals: list[ForensicSignal]
    score: float
    summary: str


# --------------------------------------------------------------------------- #
# §4  metadata  (modules/forensics)                                           #
# --------------------------------------------------------------------------- #


class MetadataDerived(TypedDict):
    created_at: str | None
    modified_at: str | None
    producer: str | None
    creator_tool: str | None
    has_gps: bool
    software_edits: list[str]


class MetadataSignal(TypedDict):
    id: str
    label: str
    score: float
    confidence: float
    passed: bool
    detail: str


class Metadata(TypedDict):
    engine: str
    engine_version: str
    container: str
    raw: dict[str, Any]
    derived: MetadataDerived
    signals: list[MetadataSignal]
    score: float
    summary: str


# --------------------------------------------------------------------------- #
# §5  consistency  (modules/consistency)                                      #
# --------------------------------------------------------------------------- #


class ConsistencyObservation(TypedDict):
    document_id: str
    value: str | None


class ConsistencyCheck(TypedDict):
    id: str
    label: str
    field: str | None
    status: Literal["pass", "warn", "fail", "not_applicable"]
    score: float
    confidence: float
    observed: list[ConsistencyObservation]
    detail: str


class ConsistencyCrossRef(TypedDict):
    check_id: str
    document_ids: list[str]


class Consistency(TypedDict):
    engine: str
    engine_version: str
    checks: list[ConsistencyCheck]
    cross_references: list[ConsistencyCrossRef]
    score: float
    summary: str


# --------------------------------------------------------------------------- #
# §6  risk  (modules/risk)                                                    #
# --------------------------------------------------------------------------- #


class RiskContribution(TypedDict):
    source: Literal["ocr", "forensics", "metadata", "consistency"]
    signal_id: str
    signal_score: float
    weight: float
    contribution: float


class RiskModelInfo(TypedDict):
    method: str
    version: str


class Risk(TypedDict):
    engine: str
    engine_version: str
    scope: Literal["document", "bundle"]
    subject_id: str
    score: float
    severity: Severity
    contributions: list[RiskContribution]
    model: RiskModelInfo


# --------------------------------------------------------------------------- #
# §7  recommendation  (modules/risk)                                          #
# --------------------------------------------------------------------------- #


class RecommendationBasis(TypedDict):
    bundle_risk_score: float
    severity: Severity


class Recommendation(TypedDict):
    decision: Literal["accept", "review", "reject"]
    confidence: float
    headline: str
    reasons: list[str]
    suggested_actions: list[str]
    based_on: RecommendationBasis


# --------------------------------------------------------------------------- #
# §8  explanation  (modules/risk)                                             #
# --------------------------------------------------------------------------- #


class ExplanationEvidence(TypedDict):
    document_id: str | None
    section: Literal["extraction", "forensics", "metadata", "consistency"]
    signal_id: str
    quote: str
    page: int | None
    bbox: list[float] | None


class ExplanationFactor(TypedDict):
    title: str
    impact: Literal["increases_risk", "decreases_risk", "neutral"]
    weight: Literal["minor", "moderate", "major"]
    evidence: list[ExplanationEvidence]


class GlossaryEntry(TypedDict):
    term: str
    definition: str


class Explanation(TypedDict):
    summary: str
    factors: list[ExplanationFactor]
    glossary: list[GlossaryEntry]


# --------------------------------------------------------------------------- #
# §9  ModuleError                                                             #
# --------------------------------------------------------------------------- #


class ModuleError(TypedDict):
    module: Literal["ocr", "forensics", "consistency", "risk", "ingest"]
    scope: Literal["document", "bundle"]
    subject_id: str
    kind: Literal["timeout", "exception", "unsupported_media", "bad_input"]
    message: str
    at: str


# --------------------------------------------------------------------------- #
# §0  VerificationReport                                                      #
# --------------------------------------------------------------------------- #


class ReportBundle(TypedDict):
    bundle_id: str
    document_count: int


class ReportDocumentEntry(TypedDict):
    document: Document
    extraction: Extraction
    forensics: Forensics
    metadata: Metadata
    risk: Risk


class VerificationReport(TypedDict):
    report_id: str
    created_at: str
    status: Literal["complete", "partial", "failed"]
    bundle: ReportBundle
    documents: list[ReportDocumentEntry]
    consistency: Consistency
    risk: Risk
    recommendation: Recommendation
    explanation: Explanation
    errors: list[ModuleError]


__all__ = [
    "Severity",
    "SEVERITY_BANDS",
    "DEFAULT_DECISION_FOR_SEVERITY",
    "severity_for_score",
    "Document",
    "DocumentPage",
    "Extraction",
    "ExtractionField",
    "ExtractionTable",
    "ExtractionPageInfo",
    "Forensics",
    "ForensicSignal",
    "ForensicRegion",
    "Metadata",
    "MetadataDerived",
    "MetadataSignal",
    "Consistency",
    "ConsistencyCheck",
    "ConsistencyObservation",
    "ConsistencyCrossRef",
    "Risk",
    "RiskContribution",
    "RiskModelInfo",
    "Recommendation",
    "RecommendationBasis",
    "Explanation",
    "ExplanationFactor",
    "ExplanationEvidence",
    "GlossaryEntry",
    "ModuleError",
    "VerificationReport",
    "ReportBundle",
    "ReportDocumentEntry",
]
