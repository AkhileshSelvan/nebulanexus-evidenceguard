# EvidenceGuard — Shared JSON Contract

**Status:** v0.1.1. **This document is the source of truth.**
Every module and both apps depend on these shapes. Do not change a field without
updating this file and notifying the team.

**v0.1.1 (OCR checkpoint):** additive only — `extraction.warnings` and
`extraction.pages` were added (§2). No existing field changed shape.

- All objects are plain JSON.
- All timestamps are ISO 8601 UTC strings (`2026-08-28T10:36:00Z`).
- All scores are numbers in `[0, 100]` unless noted; `0` = no concern,
  `100` = maximum concern.
- All `confidence` values are floats in `[0, 1]`.
- Unknown / not-yet-computed values are `null`, never omitted.
- Every module returns **only its own section**. The backend assembles the
  full `VerificationReport`.

---

## 0. Top-level: `VerificationReport`

Returned by `POST /api/v1/verify`.

```jsonc
{
  "report_id": "rep_7f3c1a92",
  "created_at": "2026-08-28T10:36:00Z",
  "status": "complete",            // "complete" | "partial" | "failed"
  "bundle": {
    "bundle_id": "bnd_1a2b3c",
    "document_count": 3
  },
  "documents": [
    {
      "document":       { /* §1  */ },
      "extraction":     { /* §2  */ },
      "forensics":      { /* §3  */ },
      "metadata":       { /* §4  */ },
      "risk":           { /* §6 per-document */ }
    }
    // ... one entry per uploaded file
  ],
  "consistency":     { /* §5  bundle-level */ },
  "risk":            { /* §6  bundle-level roll-up */ },
  "recommendation":  { /* §7  */ },
  "explanation":     { /* §8  */ },
  "errors": []                     // array of §9 ModuleError, [] when clean
}
```

`status`:
- `complete` — every module ran.
- `partial` — at least one module errored; see `errors`. Present sections are still valid.
- `failed` — ingest failed; `documents` may be empty.

---

## 1. `document`

Produced by **`backend`** (ingest & normalize). Read-only for every module.

```jsonc
{
  "id": "doc_9c8b7a",
  "bundle_id": "bnd_1a2b3c",
  "filename": "payslip_july.pdf",
  "media_type": "application/pdf",     // MIME
  "byte_size": 148213,
  "sha256": "9f2c…",                   // hash of the original bytes
  "page_count": 1,
  "declared_type": "payslip",          // caller-supplied hint, may be null
  "detected_type": "payslip",          // backend guess, may be null
  "pages": [
    {
      "page_number": 1,
      "width": 1654,                   // px, normalized raster
      "height": 2339,
      "image_ref": "doc_9c8b7a/p1.png" // path the modules can load
    }
  ],
  "received_at": "2026-08-28T10:36:00Z"
}
```

---

## 2. `extraction`  — owner: `modules/ocr`

What the document **says**. No judgement about correctness.

```jsonc
{
  "engine": "tesseract",             // engine actually used; "tesseract-unavailable" if the binary was missing
  "engine_version": "0.1.0",
  "language": "eng",
  "full_text": "ACME LTD…",
  "text_confidence": 0.0,             // overall, [0,1] — mean OCR word confidence across pages
  "fields": [
    {
      "key": "employee_name",         // snake_case, from a shared vocab (see below)
      "value": "Jane Doe",
      "value_normalized": "jane doe", // lowercased/trimmed for comparison
      "data_type": "string",          // "string"|"date"|"number"|"currency"|"id"
      "confidence": 0.0,
      "page": 1,
      "bbox": [0.12, 0.08, 0.44, 0.11] // [x0,y0,x1,y1] as page fractions, or null
    }
  ],
  "tables": [],                       // reserved; OCR does not populate tables yet
  "warnings": [                       // v0.1.1 (additive) — non-fatal notes; [] when clean
    "Tesseract OCR engine not available on this host; no text was extracted."
  ],
  "pages": [                          // v0.1.1 (additive) — one entry per page actually rasterized; [] if none
    {
      "page_number": 1,
      "source": "pdf",               // "image" | "pdf"
      "width": 1654,                  // px of the processed raster
      "height": 2339,
      "rotation_applied": 0,          // degrees the preprocessor rotated the page (0/90/180/270)
      "text_confidence": 0.0,         // [0,1] mean OCR confidence for this page
      "char_count": 0
    }
  ]
}
```

`warnings` and `pages` are **additive** (v0.1.1). Consumers that ignore them are
unaffected. The OCR module never fabricates: if the engine cannot run it returns
`full_text: ""`, `text_confidence: 0.0`, `fields: []` and an explanatory warning.

**Shared field-key vocabulary** (extend via PR): `full_name`, `first_name`,
`last_name`, `date_of_birth`, `address`, `document_number`, `issue_date`,
`expiry_date`, `issuer`, `employer_name`, `employee_name`, `pay_period_start`,
`pay_period_end`, `gross_pay`, `net_pay`, `tax`, `account_number`, `sort_code`,
`iban`, `statement_period_start`, `statement_period_end`, `opening_balance`,
`closing_balance`, `total`.
Added by `modules/ocr` (v0.1.1): `date` (an unlabelled date found in the text),
`amount` (an unlabelled monetary amount), `score` (a labelled numeric score).

---

## 3. `forensics`  — owner: `modules/forensics`

Single-document, pixel/file-level manipulation signals.

```jsonc
{
  "engine": "stub-forensics",
  "engine_version": "0.0.0",
  "signals": [
    {
      "id": "ela_hotspot",            // stable slug per check
      "label": "Error-level analysis hotspot",
      "score": 0.0,                   // [0,100] concern for THIS signal
      "confidence": 0.0,              // [0,1] how sure the check is
      "passed": true,                 // true = looks clean
      "pages": [1],
      "regions": [                    // optional, for UI overlays
        { "page": 1, "bbox": [0.30, 0.55, 0.48, 0.62], "note": "resaved region" }
      ],
      "detail": "No resave artifacts detected."
    }
  ],
  "score": 0.0,                       // [0,100] rolled up across signals
  "summary": "No manipulation signals found."
}
```

Suggested signal ids: `ela_hotspot`, `copy_move`, `noise_inconsistency`,
`double_compression`, `splicing_boundary`, `font_substitution`,
`text_layer_mismatch` (PDF text vs. rendered pixels), `annotation_overlay`.

---

## 4. `metadata`  — owner: `modules/forensics`

File-history plausibility. Split from `forensics` so it can become its own
module later without a breaking change.

```jsonc
{
  "engine": "stub-metadata",
  "engine_version": "0.0.0",
  "container": "pdf",                 // "pdf" | "jpeg" | "png" | "docx" | …
  "raw": {                            // best-effort passthrough, keys vary
    "Producer": "iText 2.1.7",
    "CreationDate": "2026-07-31T09:00:00Z",
    "ModDate": "2026-07-31T09:02:11Z"
  },
  "derived": {
    "created_at": "2026-07-31T09:00:00Z",
    "modified_at": "2026-07-31T09:02:11Z",
    "producer": "iText 2.1.7",
    "creator_tool": null,
    "has_gps": false,
    "software_edits": ["iText 2.1.7"] // editor chain if recoverable
  },
  "signals": [
    {
      "id": "modified_after_creation",
      "label": "Modified shortly after creation",
      "score": 0.0,
      "confidence": 0.0,
      "passed": true,
      "detail": "2 minute gap — within normal range."
    }
  ],
  "score": 0.0,
  "summary": "Metadata is internally consistent."
}
```

Suggested signal ids: `modified_after_creation`, `future_timestamp`,
`timezone_mismatch`, `editor_is_image_tool`, `missing_expected_metadata`,
`producer_mismatch_for_issuer`.

---

## 5. `consistency`  — owner: `modules/consistency`

Bundle-level. Compares the `extraction` output of **every** document.

```jsonc
{
  "engine": "stub-consistency",
  "engine_version": "0.0.0",
  "checks": [
    {
      "id": "name_match",
      "label": "Name matches across documents",
      "field": "full_name",
      "status": "pass",              // "pass" | "warn" | "fail" | "not_applicable"
      "score": 0.0,                  // [0,100] concern
      "confidence": 0.0,
      "observed": [
        { "document_id": "doc_9c8b7a", "value": "Jane Doe" },
        { "document_id": "doc_5d4e3f", "value": "Jane A. Doe" }
      ],
      "detail": "Minor vari: middle initial present on one document."
    }
  ],
  "cross_references": [              // which docs each check tied together
    { "check_id": "name_match", "document_ids": ["doc_9c8b7a", "doc_5d4e3f"] }
  ],
  "score": 0.0,                     // [0,100] rolled up
  "summary": "Documents are mutually consistent."
}
```

Suggested check ids: `name_match`, `dob_match`, `address_match`,
`document_number_reuse`, `date_ordering` (issue < expiry, period start < end),
`amount_arithmetic` (gross − deductions = net), `issuer_expected`,
`period_overlap`, `template_match`.

---

## 6. `risk`  — owner: `modules/risk`

Emitted at **two levels** with the *same shape*: once per document
(`documents[].risk`) and once for the bundle (top-level `risk`).

```jsonc
{
  "engine": "evidenceguard-risk",
  "engine_version": "1.0.0",
  "scope": "document",              // "document" | "bundle"
  "subject_id": "doc_9c8b7a",       // document id, or bundle id when scope=bundle
  "score": 0.0,                     // [0,100] final risk
  "severity": "low",               // "low"|"medium"|"high"|"critical" (see bands)
  "contributions": [               // what moved the score, sorted desc by `contribution`
    {
      "source": "forensics",       // "ocr"|"forensics"|"metadata"|"consistency"
      "signal_id": "ela_hotspot",  // scope=bundle adds a document tag — see below
      "signal_score": 0.0,         // [0,100] as reported by the producing module
      "weight": 0.0,               // [0,1] the source weight applied to this signal
      "contribution": 0.0          // points of `score` this signal is responsible for
    }
  ],
  "model": {
    "method": "bounded_log_noisy_or",  // implementation detail, informational
    "version": "1.0.0"
  }
}
```

**`contributions[].signal_id` — document tagging.** When `scope` is `"bundle"`,
a signal that came from a specific document is tagged
`"<signal_id>@<document_id>"` (e.g. `"ela_hotspot@doc_9c8b7a"`) so the same check
firing on several documents stays distinguishable. Bundle-scoped signals
(consistency checks) carry no tag. Producing modules **may** use `@` inside their
own ids, so always split the tag from the **right** — the last `@` is the
separator. Document-scoped `Risk` objects are never tagged.

**`contributions[].contribution` sums to `score`.** The fusion is additive in log
space, so `sum(contributions[].contribution) == score` up to rounding. Consumers
may rely on that identity.

**Severity bands** (fixed, shared by UI and tests):

| Band | `score` range |
|------|---------------|
| `low` | `0 – 24` |
| `medium` | `25 – 49` |
| `high` | `50 – 74` |
| `critical` | `75 – 100` |

---

## 7. `recommendation`  — owner: `modules/risk`

The action a reviewer should take for the **bundle**.

```jsonc
{
  "decision": "review",            // "accept" | "review" | "reject"
  "confidence": 0.0,               // [0,1]
  "headline": "Manual review recommended",
  "reasons": [                     // short, ordered, most important first
    "One document shows a metadata edit gap.",
    "Address differs between the ID and the bank statement."
  ],
  "suggested_actions": [           // optional, concrete next steps
    "Request an original PDF from the issuer.",
    "Confirm current address with the applicant."
  ],
  "based_on": {
    "bundle_risk_score": 0.0,
    "severity": "medium"
  }
}
```

Mapping from severity → default `decision` (risk module may override with a
reason): `low → accept`, `medium → review`, `high → review`, `critical → reject`.

---

## 8. `explanation`  — owner: `modules/risk`

Human-facing narrative for the whole report. Pure presentation data — no new
numbers that aren't traceable to a section above.

```jsonc
{
  "summary": "The bundle is broadly consistent, but two signals need a human.",
  "factors": [
    {
      "title": "Metadata edited after creation",
      "impact": "increases_risk",   // "increases_risk"|"decreases_risk"|"neutral"
      "weight": "moderate",         // "minor"|"moderate"|"major"
      "evidence": [
        {
          "document_id": "doc_9c8b7a",
          "section": "metadata",     // which section §2–§5 this came from
          "signal_id": "modified_after_creation",
          "quote": "ModDate is 2 minutes after CreationDate",
          "page": null,
          "bbox": null
        }
      ]
    }
  ],
  "glossary": [
    { "term": "ELA", "definition": "Error-level analysis: highlights areas re-saved at a different JPEG quality." }
  ]
}
```

---

## 9. `ModuleError`

Collected in `VerificationReport.errors`. A failing module never aborts the
report — the backend records this and continues.

```jsonc
{
  "module": "forensics",           // "ocr"|"forensics"|"consistency"|"risk"|"ingest"
  "scope": "document",             // "document" | "bundle"
  "subject_id": "doc_9c8b7a",
  "kind": "timeout",               // "timeout"|"exception"|"unsupported_media"|"bad_input"
  "message": "Forensics stub raised NotImplementedError",
  "at": "2026-08-28T10:36:03Z"
}
```

---

## 10. HTTP endpoints (foundation)

| Method | Path | Body | Returns |
|--------|------|------|---------|
| `GET` | `/health` | — | `{ "status": "ok", "service": "evidenceguard-backend", "version": "0.1.0", "time": "…" }` |
| `GET` | `/api/v1/ping` | — | `{ "message": "pong" }` |
| `POST` | `/api/v1/verify` | `multipart/form-data`: 1..n `files`, optional `declared_types` | `VerificationReport` (§0) |

`POST /api/v1/verify` is **stubbed** for this checkpoint: it ingests real files
(so `document` and `metadata.raw` are real) and calls each module, which returns
contract-shaped placeholder data. No real OCR/forensic/AI work happens yet.

---

## 11. Python contract module

`modules/contract.py` holds `TypedDict` definitions matching every section here,
plus `SEVERITY_BANDS` and helper `severity_for_score(score) -> str`. Modules
import their types from there so a contract change breaks `mypy`, not prod.
