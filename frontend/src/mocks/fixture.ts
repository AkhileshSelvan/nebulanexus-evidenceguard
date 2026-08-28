// ---------------------------------------------------------------------------
// Mock VerificationReport fixture – realistic 3-document bundle
// Used when the backend is offline or for demo purposes.
// ---------------------------------------------------------------------------

import type { VerificationReport } from "../types";

export const MOCK_REPORT: VerificationReport = {
  report_id: "rep_demo_7f3c1a92",
  created_at: "2026-08-28T10:36:00Z",
  status: "complete",
  bundle: {
    bundle_id: "bnd_demo_1a2b3c",
    document_count: 3,
  },

  documents: [
    // ── Document 1: Government ID ────────────────────────────────────────
    {
      document: {
        id: "doc_id_001",
        bundle_id: "bnd_demo_1a2b3c",
        filename: "national_id_front.jpg",
        media_type: "image/jpeg",
        byte_size: 245_120,
        sha256: "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
        page_count: 1,
        declared_type: "government_id",
        detected_type: "government_id",
        pages: [{ page_number: 1, width: 1654, height: 1040, image_ref: "doc_id_001/p1.png" }],
        received_at: "2026-08-28T10:35:58Z",
      },
      extraction: {
        engine: "tesseract",
        engine_version: "0.1.0",
        language: "eng",
        full_text: "REPUBLIC OF FREEDONIA\nNATIONAL IDENTITY CARD\nName: Jane Annabelle Doe\nDate of Birth: 15/03/1990\nID No: FRD-9903150042\nAddress: 42 Maple Avenue, Rivertown\nIssued: 01/01/2024  Expires: 31/12/2034",
        text_confidence: 0.91,
        fields: [
          { key: "full_name", value: "Jane Annabelle Doe", value_normalized: "jane annabelle doe", data_type: "string", confidence: 0.95, page: 1, bbox: [0.22, 0.30, 0.78, 0.36] },
          { key: "date_of_birth", value: "15/03/1990", value_normalized: "1990-03-15", data_type: "date", confidence: 0.93, page: 1, bbox: [0.22, 0.38, 0.55, 0.43] },
          { key: "document_number", value: "FRD-9903150042", value_normalized: "frd-9903150042", data_type: "id", confidence: 0.97, page: 1, bbox: [0.22, 0.45, 0.62, 0.50] },
          { key: "address", value: "42 Maple Avenue, Rivertown", value_normalized: "42 maple avenue, rivertown", data_type: "string", confidence: 0.88, page: 1, bbox: [0.22, 0.53, 0.85, 0.58] },
          { key: "issue_date", value: "01/01/2024", value_normalized: "2024-01-01", data_type: "date", confidence: 0.90, page: 1, bbox: [0.22, 0.62, 0.48, 0.67] },
          { key: "expiry_date", value: "31/12/2034", value_normalized: "2034-12-31", data_type: "date", confidence: 0.90, page: 1, bbox: [0.55, 0.62, 0.80, 0.67] },
        ],
        tables: [],
        warnings: [],
        pages: [{ page_number: 1, source: "image", width: 1654, height: 1040, rotation_applied: 0, text_confidence: 0.91, char_count: 198 }],
      },
      forensics: {
        engine: "stub-forensics",
        engine_version: "0.0.0",
        signals: [
          { id: "ela_hotspot", label: "Error-level analysis hotspot", score: 0, confidence: 0.85, passed: true, pages: [1], regions: [], detail: "No resave artifacts detected." },
          { id: "copy_move", label: "Copy-move detection", score: 0, confidence: 0.80, passed: true, pages: [1], regions: [], detail: "No duplicated regions found." },
          { id: "noise_inconsistency", label: "Noise inconsistency", score: 12, confidence: 0.60, passed: true, pages: [1], regions: [{ page: 1, bbox: [0.70, 0.25, 0.95, 0.55], note: "Photo area has different noise profile" }], detail: "Mild noise pattern difference around the photo area — consistent with a scanned ID card." },
        ],
        score: 8,
        summary: "No significant manipulation signals. Mild noise variance is normal for scanned ID cards.",
      },
      metadata: {
        engine: "stub-metadata",
        engine_version: "0.0.0",
        container: "jpeg",
        raw: { "JFIF Version": "1.01", "Resolution": "300 dpi", "Software": "HP Scan" },
        derived: { created_at: null, modified_at: null, producer: null, creator_tool: "HP Scan", has_gps: false, software_edits: ["HP Scan"] },
        signals: [
          { id: "missing_expected_metadata", label: "Missing EXIF creation date", score: 10, confidence: 0.50, passed: true, detail: "No EXIF date — common for scanner output." },
        ],
        score: 5,
        summary: "Scanned image with minimal metadata. No anomalies.",
      },
      risk: {
        engine: "stub-risk",
        engine_version: "0.0.0",
        scope: "document",
        subject_id: "doc_id_001",
        score: 12,
        severity: "low",
        contributions: [
          { source: "forensics", signal_id: "noise_inconsistency", signal_score: 12, weight: 0.3, contribution: 3.6 },
          { source: "metadata", signal_id: "missing_expected_metadata", signal_score: 10, weight: 0.2, contribution: 2.0 },
        ],
        model: { method: "weighted_sum", version: "0.0.0" },
      },
    },

    // ── Document 2: Payslip ─────────────────────────────────────────────
    {
      document: {
        id: "doc_pay_002",
        bundle_id: "bnd_demo_1a2b3c",
        filename: "payslip_july_2026.pdf",
        media_type: "application/pdf",
        byte_size: 148_213,
        sha256: "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3",
        page_count: 1,
        declared_type: "payslip",
        detected_type: "payslip",
        pages: [{ page_number: 1, width: 1654, height: 2339, image_ref: "doc_pay_002/p1.png" }],
        received_at: "2026-08-28T10:35:59Z",
      },
      extraction: {
        engine: "tesseract",
        engine_version: "0.1.0",
        language: "eng",
        full_text: "ACME CORPORATION LTD\nPayslip — July 2026\nEmployee: Jane Doe\nEmployee ID: EMP-4471\nPay Period: 01/07/2026 – 31/07/2026\nGross Pay: £4,250.00\nTax: £850.00\nNational Insurance: £382.50\nNet Pay: £3,017.50",
        text_confidence: 0.94,
        fields: [
          { key: "employer_name", value: "ACME CORPORATION LTD", value_normalized: "acme corporation ltd", data_type: "string", confidence: 0.96, page: 1, bbox: [0.10, 0.05, 0.65, 0.09] },
          { key: "employee_name", value: "Jane Doe", value_normalized: "jane doe", data_type: "string", confidence: 0.95, page: 1, bbox: [0.25, 0.18, 0.55, 0.22] },
          { key: "pay_period_start", value: "01/07/2026", value_normalized: "2026-07-01", data_type: "date", confidence: 0.92, page: 1, bbox: [0.25, 0.26, 0.50, 0.30] },
          { key: "pay_period_end", value: "31/07/2026", value_normalized: "2026-07-31", data_type: "date", confidence: 0.92, page: 1, bbox: [0.55, 0.26, 0.78, 0.30] },
          { key: "gross_pay", value: "£4,250.00", value_normalized: "4250.00", data_type: "currency", confidence: 0.97, page: 1, bbox: [0.60, 0.36, 0.88, 0.40] },
          { key: "tax", value: "£850.00", value_normalized: "850.00", data_type: "currency", confidence: 0.96, page: 1, bbox: [0.60, 0.42, 0.88, 0.46] },
          { key: "net_pay", value: "£3,017.50", value_normalized: "3017.50", data_type: "currency", confidence: 0.96, page: 1, bbox: [0.60, 0.54, 0.88, 0.58] },
        ],
        tables: [],
        warnings: [],
        pages: [{ page_number: 1, source: "pdf", width: 1654, height: 2339, rotation_applied: 0, text_confidence: 0.94, char_count: 312 }],
      },
      forensics: {
        engine: "stub-forensics",
        engine_version: "0.0.0",
        signals: [
          { id: "ela_hotspot", label: "Error-level analysis hotspot", score: 45, confidence: 0.75, passed: false, pages: [1], regions: [{ page: 1, bbox: [0.58, 0.34, 0.90, 0.60], note: "ELA bright patch around pay figures" }], detail: "Elevated error-level intensity around the salary figures. Consistent with re-editing or re-saving at different quality." },
          { id: "font_substitution", label: "Font substitution detected", score: 38, confidence: 0.70, passed: false, pages: [1], regions: [{ page: 1, bbox: [0.58, 0.50, 0.90, 0.60], note: "Net pay uses different font metrics" }], detail: "The net pay field uses slightly different font metrics than the rest of the document." },
          { id: "text_layer_mismatch", label: "PDF text layer vs rendered pixels", score: 0, confidence: 0.90, passed: true, pages: [1], regions: [], detail: "Text layer and rendered image are in agreement." },
        ],
        score: 52,
        summary: "Elevated ELA signal and font irregularity near salary figures. Manual review recommended.",
      },
      metadata: {
        engine: "stub-metadata",
        engine_version: "0.0.0",
        container: "pdf",
        raw: { "Producer": "iText 2.1.7", "CreationDate": "2026-07-31T09:00:00Z", "ModDate": "2026-08-15T14:22:11Z" },
        derived: { created_at: "2026-07-31T09:00:00Z", modified_at: "2026-08-15T14:22:11Z", producer: "iText 2.1.7", creator_tool: null, has_gps: false, software_edits: ["iText 2.1.7"] },
        signals: [
          { id: "modified_after_creation", label: "Modified well after creation", score: 55, confidence: 0.85, passed: false, detail: "ModDate is 15 days after CreationDate — unusual for an auto-generated payslip." },
          { id: "editor_is_image_tool", label: "Producer is a developer toolkit", score: 20, confidence: 0.60, passed: true, detail: "iText is a PDF library, used both legitimately and for editing." },
        ],
        score: 48,
        summary: "PDF was modified 15 days after creation. Producer is a developer toolkit.",
      },
      risk: {
        engine: "stub-risk",
        engine_version: "0.0.0",
        scope: "document",
        subject_id: "doc_pay_002",
        score: 58,
        severity: "high",
        contributions: [
          { source: "forensics", signal_id: "ela_hotspot", signal_score: 45, weight: 0.35, contribution: 15.75 },
          { source: "metadata", signal_id: "modified_after_creation", signal_score: 55, weight: 0.25, contribution: 13.75 },
          { source: "forensics", signal_id: "font_substitution", signal_score: 38, weight: 0.25, contribution: 9.50 },
          { source: "metadata", signal_id: "editor_is_image_tool", signal_score: 20, weight: 0.15, contribution: 3.00 },
        ],
        model: { method: "weighted_sum", version: "0.0.0" },
      },
    },

    // ── Document 3: Bank Statement ──────────────────────────────────────
    {
      document: {
        id: "doc_bank_003",
        bundle_id: "bnd_demo_1a2b3c",
        filename: "bank_statement_aug.pdf",
        media_type: "application/pdf",
        byte_size: 312_400,
        sha256: "c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
        page_count: 2,
        declared_type: "bank_statement",
        detected_type: "bank_statement",
        pages: [
          { page_number: 1, width: 1654, height: 2339, image_ref: "doc_bank_003/p1.png" },
          { page_number: 2, width: 1654, height: 2339, image_ref: "doc_bank_003/p2.png" },
        ],
        received_at: "2026-08-28T10:36:00Z",
      },
      extraction: {
        engine: "tesseract",
        engine_version: "0.1.0",
        language: "eng",
        full_text: "FREEDONIA NATIONAL BANK\nStatement Period: 01/07/2026 – 31/07/2026\nAccount Holder: Jane A. Doe\nAccount No: ****7821\nSort Code: 40-12-56\nOpening Balance: £8,420.12\nDeposits: £3,017.50 (ACME CORP — salary)\nWithdrawals: £2,150.00\nClosing Balance: £9,287.62",
        text_confidence: 0.93,
        fields: [
          { key: "full_name", value: "Jane A. Doe", value_normalized: "jane a. doe", data_type: "string", confidence: 0.94, page: 1, bbox: [0.15, 0.18, 0.55, 0.22] },
          { key: "account_number", value: "****7821", value_normalized: "****7821", data_type: "id", confidence: 0.98, page: 1, bbox: [0.15, 0.26, 0.45, 0.30] },
          { key: "sort_code", value: "40-12-56", value_normalized: "40-12-56", data_type: "id", confidence: 0.97, page: 1, bbox: [0.50, 0.26, 0.75, 0.30] },
          { key: "statement_period_start", value: "01/07/2026", value_normalized: "2026-07-01", data_type: "date", confidence: 0.91, page: 1, bbox: [0.35, 0.12, 0.55, 0.15] },
          { key: "statement_period_end", value: "31/07/2026", value_normalized: "2026-07-31", data_type: "date", confidence: 0.91, page: 1, bbox: [0.60, 0.12, 0.80, 0.15] },
          { key: "opening_balance", value: "£8,420.12", value_normalized: "8420.12", data_type: "currency", confidence: 0.96, page: 1, bbox: [0.60, 0.34, 0.88, 0.38] },
          { key: "closing_balance", value: "£9,287.62", value_normalized: "9287.62", data_type: "currency", confidence: 0.96, page: 2, bbox: [0.60, 0.85, 0.88, 0.89] },
          { key: "address", value: "15 Oak Lane, Greenfield", value_normalized: "15 oak lane, greenfield", data_type: "string", confidence: 0.87, page: 1, bbox: [0.15, 0.32, 0.60, 0.36] },
        ],
        tables: [],
        warnings: [],
        pages: [
          { page_number: 1, source: "pdf", width: 1654, height: 2339, rotation_applied: 0, text_confidence: 0.94, char_count: 420 },
          { page_number: 2, source: "pdf", width: 1654, height: 2339, rotation_applied: 0, text_confidence: 0.92, char_count: 380 },
        ],
      },
      forensics: {
        engine: "stub-forensics",
        engine_version: "0.0.0",
        signals: [
          { id: "ela_hotspot", label: "Error-level analysis hotspot", score: 0, confidence: 0.88, passed: true, pages: [1, 2], regions: [], detail: "No resave artifacts detected." },
          { id: "double_compression", label: "Double JPEG compression", score: 0, confidence: 0.82, passed: true, pages: [1, 2], regions: [], detail: "No double compression artifacts." },
        ],
        score: 0,
        summary: "No manipulation signals found.",
      },
      metadata: {
        engine: "stub-metadata",
        engine_version: "0.0.0",
        container: "pdf",
        raw: { "Producer": "Freedonia National Bank / Statements v3.2", "CreationDate": "2026-08-01T06:00:00Z", "ModDate": "2026-08-01T06:00:01Z" },
        derived: { created_at: "2026-08-01T06:00:00Z", modified_at: "2026-08-01T06:00:01Z", producer: "Freedonia National Bank / Statements v3.2", creator_tool: null, has_gps: false, software_edits: ["Freedonia National Bank / Statements v3.2"] },
        signals: [
          { id: "modified_after_creation", label: "Modified shortly after creation", score: 0, confidence: 0.95, passed: true, detail: "1-second gap — normal for auto-generated statements." },
        ],
        score: 0,
        summary: "Metadata is internally consistent. Auto-generated bank statement.",
      },
      risk: {
        engine: "stub-risk",
        engine_version: "0.0.0",
        scope: "document",
        subject_id: "doc_bank_003",
        score: 5,
        severity: "low",
        contributions: [],
        model: { method: "weighted_sum", version: "0.0.0" },
      },
    },
  ],

  // ── Bundle-level consistency ──────────────────────────────────────────
  consistency: {
    engine: "stub-consistency",
    engine_version: "0.0.0",
    checks: [
      {
        id: "name_match",
        label: "Name matches across documents",
        field: "full_name",
        status: "warn",
        score: 25,
        confidence: 0.80,
        observed: [
          { document_id: "doc_id_001", value: "Jane Annabelle Doe" },
          { document_id: "doc_pay_002", value: "Jane Doe" },
          { document_id: "doc_bank_003", value: "Jane A. Doe" },
        ],
        detail: "Minor variation: middle name present on ID, initial on statement, absent on payslip.",
      },
      {
        id: "address_match",
        label: "Address matches across documents",
        field: "address",
        status: "fail",
        score: 65,
        confidence: 0.85,
        observed: [
          { document_id: "doc_id_001", value: "42 Maple Avenue, Rivertown" },
          { document_id: "doc_bank_003", value: "15 Oak Lane, Greenfield" },
        ],
        detail: "Addresses differ entirely between the ID and the bank statement.",
      },
      {
        id: "date_ordering",
        label: "Pay period aligns with statement period",
        field: "pay_period",
        status: "pass",
        score: 0,
        confidence: 0.92,
        observed: [
          { document_id: "doc_pay_002", value: "01/07/2026 – 31/07/2026" },
          { document_id: "doc_bank_003", value: "01/07/2026 – 31/07/2026" },
        ],
        detail: "Pay period and statement period match exactly.",
      },
      {
        id: "amount_arithmetic",
        label: "Net pay equals deposit on statement",
        field: "net_pay",
        status: "pass",
        score: 0,
        confidence: 0.95,
        observed: [
          { document_id: "doc_pay_002", value: "£3,017.50" },
          { document_id: "doc_bank_003", value: "£3,017.50 (ACME CORP — salary)" },
        ],
        detail: "Net pay on the payslip matches the salary deposit on the bank statement.",
      },
    ],
    cross_references: [
      { check_id: "name_match", document_ids: ["doc_id_001", "doc_pay_002", "doc_bank_003"] },
      { check_id: "address_match", document_ids: ["doc_id_001", "doc_bank_003"] },
      { check_id: "date_ordering", document_ids: ["doc_pay_002", "doc_bank_003"] },
      { check_id: "amount_arithmetic", document_ids: ["doc_pay_002", "doc_bank_003"] },
    ],
    score: 35,
    summary: "Address mismatch detected. Name variation is minor but should be verified.",
  },

  // ── Bundle-level risk ─────────────────────────────────────────────────
  risk: {
    engine: "stub-risk",
    engine_version: "0.0.0",
    scope: "bundle",
    subject_id: "bnd_demo_1a2b3c",
    score: 46,
    severity: "medium",
    contributions: [
      { source: "forensics", signal_id: "ela_hotspot", signal_score: 45, weight: 0.25, contribution: 11.25 },
      { source: "metadata", signal_id: "modified_after_creation", signal_score: 55, weight: 0.20, contribution: 11.00 },
      { source: "consistency", signal_id: "address_match", signal_score: 65, weight: 0.20, contribution: 13.00 },
      { source: "forensics", signal_id: "font_substitution", signal_score: 38, weight: 0.15, contribution: 5.70 },
      { source: "consistency", signal_id: "name_match", signal_score: 25, weight: 0.10, contribution: 2.50 },
    ],
    model: { method: "weighted_sum", version: "0.0.0" },
  },

  // ── Recommendation ────────────────────────────────────────────────────
  recommendation: {
    decision: "review",
    confidence: 0.78,
    headline: "Manual review recommended",
    reasons: [
      "The payslip PDF was modified 15 days after creation with elevated ELA around salary figures.",
      "Address on the government ID does not match the address on the bank statement.",
      "Minor name variation across all three documents.",
    ],
    suggested_actions: [
      "Request an original, unedited payslip directly from the employer.",
      "Confirm the applicant's current address — the ID may be outdated.",
      "Cross-check the salary deposit (£3,017.50) with employer HR records.",
    ],
    based_on: {
      bundle_risk_score: 46,
      severity: "medium",
    },
  },

  // ── Explanation ───────────────────────────────────────────────────────
  explanation: {
    summary: "The bundle is broadly consistent on dates and pay amounts, but two signals need a human eye: the payslip shows signs of post-creation editing, and the addresses on the ID and bank statement don't match.",
    factors: [
      {
        title: "Payslip edited after creation",
        impact: "increases_risk",
        weight: "major",
        evidence: [
          { document_id: "doc_pay_002", section: "forensics", signal_id: "ela_hotspot", quote: "Elevated error-level intensity around the salary figures", page: 1, bbox: [0.58, 0.34, 0.90, 0.60] },
          { document_id: "doc_pay_002", section: "metadata", signal_id: "modified_after_creation", quote: "ModDate is 15 days after CreationDate", page: null, bbox: null },
        ],
      },
      {
        title: "Address mismatch between ID and bank statement",
        impact: "increases_risk",
        weight: "moderate",
        evidence: [
          { document_id: "doc_id_001", section: "consistency", signal_id: "address_match", quote: "42 Maple Avenue, Rivertown", page: 1, bbox: [0.22, 0.53, 0.85, 0.58] },
          { document_id: "doc_bank_003", section: "consistency", signal_id: "address_match", quote: "15 Oak Lane, Greenfield", page: 1, bbox: [0.15, 0.32, 0.60, 0.36] },
        ],
      },
      {
        title: "Pay-period dates and net-pay amount match",
        impact: "decreases_risk",
        weight: "moderate",
        evidence: [
          { document_id: "doc_pay_002", section: "consistency", signal_id: "amount_arithmetic", quote: "Net pay £3,017.50 matches salary deposit", page: null, bbox: null },
        ],
      },
      {
        title: "Font metrics differ on net pay field",
        impact: "increases_risk",
        weight: "minor",
        evidence: [
          { document_id: "doc_pay_002", section: "forensics", signal_id: "font_substitution", quote: "Net pay field uses slightly different font metrics", page: 1, bbox: [0.58, 0.50, 0.90, 0.60] },
        ],
      },
    ],
    glossary: [
      { term: "ELA", definition: "Error-level analysis: highlights areas re-saved at a different JPEG quality, which can indicate editing." },
      { term: "Copy-move", definition: "Detection of duplicated regions within a single image, a common sign of cloning edits." },
      { term: "iText", definition: "A PDF generation and manipulation library. Legitimate use is common, but it can also be used to alter documents." },
    ],
  },

  errors: [],
};
