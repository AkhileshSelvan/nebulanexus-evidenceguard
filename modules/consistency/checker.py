"""Cross-document consistency checks.

Owner: Consistency developer.
Produces: ``Consistency`` (contract §5).

Compares the ``ExtractionField`` values every document's OCR output already
found (see ``modules/ocr``) against the *other* documents in the same
bundle. Nothing here re-reads pixels or re-runs OCR -- this module only
compares values that were already, honestly, extracted.

Checks implemented (see README for the full suggested list):

  * ``name_match``, ``dob_match``, ``address_match`` -- do documents agree
    on who/where this is about?
  * ``document_number_reuse`` -- does one document number turn up on more
    than one document in the bundle?
  * ``date_ordering`` -- within a document, is issue_date before
    expiry_date (and pay_period_start before pay_period_end, if present)?
  * ``amount_arithmetic`` -- within a document, does gross_pay - tax
    reconcile with net_pay (or at least net <= gross)?

A check only appears with a real ``status`` when there was something to
compare; otherwise it is ``not_applicable`` -- this module never invents a
finding to fill out the list, mirroring the "never fabricate" rule OCR
follows for fields it can't find.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher

from modules.contract import (
    Consistency,
    ConsistencyCheck,
    ConsistencyCrossRef,
    ConsistencyObservation,
    Document,
    Extraction,
    ExtractionField,
)

ENGINE = "consistency-v1"
ENGINE_VERSION = "0.1.0"

# Fuzzy-match thresholds (SequenceMatcher ratio, [0,1]). Tuned for OCR noise:
# a couple of swapped/garbled characters shouldn't read as a real mismatch,
# but a genuinely different name/address should.
_FUZZY_PASS = 0.92   # near-identical -> pass
_FUZZY_WARN = 0.75   # plausibly-the-same-thing-with-noise -> warn
# below _FUZZY_WARN -> fail

_ARITHMETIC_TOLERANCE = 0.02  # 2% -- absorbs rounding / OCR digit noise


# --------------------------------------------------------------------------- #
# small shared helpers                                                        #
# --------------------------------------------------------------------------- #


def _fields_by_key(extraction: Extraction, key: str) -> list[ExtractionField]:
    return [f for f in extraction["fields"] if f["key"] == key]


def _best_value(extraction: Extraction, key: str) -> ExtractionField | None:
    """Highest-confidence field for ``key`` on one document, or ``None``."""
    candidates = _fields_by_key(extraction, key)
    if not candidates:
        return None
    return max(candidates, key=lambda f: f["confidence"])


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(a=a, b=b).ratio()


def _to_number(raw: str | None) -> float | None:
    if raw is None:
        return None
    cleaned = raw.replace(",", "").replace(" ", "")
    for prefix in ("₹", "rs.", "rs", "inr", "$", "usd", "us$", "€", "eur", "£", "gbp"):
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    try:
        return float(cleaned)
    except ValueError:
        return None


@dataclass
class _CheckBuilder:
    """Accumulates one ``ConsistencyCheck`` + the doc ids it touched."""

    id: str
    label: str
    field: str | None
    observed: list[ConsistencyObservation] = field(default_factory=list)
    document_ids: list[str] = field(default_factory=list)

    def observe(self, document_id: str, value: str | None) -> None:
        self.observed.append(ConsistencyObservation(document_id=document_id, value=value))
        if document_id not in self.document_ids:
            self.document_ids.append(document_id)

    def result(
        self, status: str, score: float, confidence: float, detail: str
    ) -> tuple[ConsistencyCheck, ConsistencyCrossRef | None]:
        check = ConsistencyCheck(
            id=self.id,
            label=self.label,
            field=self.field,
            status=status,  # type: ignore[typeddict-item]
            score=round(max(0.0, min(100.0, score)), 2),
            confidence=round(max(0.0, min(1.0, confidence)), 4),
            observed=self.observed,
            detail=detail,
        )
        crossref = (
            ConsistencyCrossRef(check_id=self.id, document_ids=self.document_ids)
            if len(self.document_ids) >= 2
            else None
        )
        return check, crossref


def _not_applicable(check_id: str, label: str, field_key: str | None, detail: str) -> ConsistencyCheck:
    return ConsistencyCheck(
        id=check_id,
        label=label,
        field=field_key,
        status="not_applicable",
        score=0.0,
        confidence=0.0,
        observed=[],
        detail=detail,
    )


# --------------------------------------------------------------------------- #
# cross-document field-agreement checks                                       #
# --------------------------------------------------------------------------- #


def _check_field_agreement(
    check_id: str,
    label: str,
    field_key: str,
    documents: list[Document],
    extractions: list[Extraction],
    *,
    exact_only: bool,
) -> tuple[ConsistencyCheck, ConsistencyCrossRef | None]:
    """Compare one field across every document that has it.

    ``exact_only``: DOB-like fields where any disagreement is a real
    finding (normalized values either match or they don't). When ``False``
    (names, addresses), OCR noise is expected, so near-matches ``warn``
    instead of ``fail``.
    """
    builder = _CheckBuilder(id=check_id, label=label, field=field_key)
    present: list[tuple[Document, ExtractionField]] = []
    for doc, extraction in zip(documents, extractions):
        best = _best_value(extraction, field_key)
        if best is not None and best["value"]:
            present.append((doc, best))
            builder.observe(doc["id"], best["value"])

    if len(present) < 2:
        return (
            _not_applicable(
                check_id, label, field_key,
                f"{field_key} present on fewer than 2 documents; nothing to compare.",
            ),
            None,
        )

    # Compare every pair; keep the worst (lowest-similarity) pair as the
    # representative finding -- one bad pair should not be diluted by
    # several good ones.
    worst_ratio = 1.0
    worst_pair: tuple[str, str] | None = None
    all_exact = True
    for i in range(len(present)):
        for j in range(i + 1, len(present)):
            va = (present[i][1]["value_normalized"] or present[i][1]["value"] or "").lower()
            vb = (present[j][1]["value_normalized"] or present[j][1]["value"] or "").lower()
            exact = va == vb
            all_exact = all_exact and exact
            ratio = 1.0 if exact else _similarity(va, vb)
            if ratio < worst_ratio:
                worst_ratio = ratio
                worst_pair = (present[i][0]["id"], present[j][0]["id"])

    avg_conf = sum(f["confidence"] for _, f in present) / len(present)
    left = worst_pair[0] if worst_pair else "?"
    right = worst_pair[1] if worst_pair else "?"

    if all_exact:
        return builder.result(
            "pass", 0.0, avg_conf, f"{field_key} agrees exactly across {len(present)} document(s).",
        )

    if exact_only:
        # No fuzzy middle ground for a field like DOB: it either matches
        # exactly or it's a real discrepancy, however textually close the
        # two strings happen to look (e.g. "1998-07-15" vs "1998-07-16").
        return builder.result(
            "fail", round((1.0 - worst_ratio) * 100, 2), avg_conf,
            f"{field_key} differs between {left} and {right}; this field is expected to match exactly.",
        )

    if worst_ratio >= _FUZZY_PASS:
        # Not byte-identical, but near-identical (e.g. stray punctuation
        # OCR noise that survived normalization) -- close enough to pass.
        return builder.result(
            "pass", round((1.0 - worst_ratio) * 20, 2), avg_conf,
            f"{field_key} agrees (near-identical) across {len(present)} document(s).",
        )

    if worst_ratio >= _FUZZY_WARN:
        return builder.result(
            "warn", round((1.0 - worst_ratio) * 100, 2), avg_conf,
            f"{field_key} is a close-but-not-exact match between {left} and {right} -- "
            "likely OCR noise or a minor variant (e.g. a middle initial).",
        )
    return builder.result(
        "fail", round((1.0 - worst_ratio) * 100, 2), avg_conf,
        f"{field_key} differs substantially between {left} and {right}.",
    )


# --------------------------------------------------------------------------- #
# document_number_reuse                                                       #
# --------------------------------------------------------------------------- #


def _check_document_number_reuse(
    documents: list[Document], extractions: list[Extraction]
) -> tuple[ConsistencyCheck, ConsistencyCrossRef | None]:
    check_id, label, field_key = "document_number_reuse", "Document number reused across documents", "document_number"
    builder = _CheckBuilder(id=check_id, label=label, field=field_key)

    by_value: dict[str, list[tuple[str, ExtractionField]]] = {}
    for doc, extraction in zip(documents, extractions):
        for f in _fields_by_key(extraction, "document_number"):
            key = (f["value_normalized"] or f["value"] or "").strip()
            if not key:
                continue
            by_value.setdefault(key, []).append((doc["id"], f))

    reused = {v: entries for v, entries in by_value.items() if len({d for d, _ in entries}) >= 2}
    if not reused:
        return (
            _not_applicable(
                check_id, label, field_key,
                "No document_number value appears on more than one document.",
            ),
            None,
        )

    for value, entries in reused.items():
        for doc_id, f in entries:
            builder.observe(doc_id, f["value"])

    worst_value, worst_entries = max(reused.items(), key=lambda kv: len(kv[1]))
    doc_count = len({d for d, _ in worst_entries})
    avg_conf = sum(f["confidence"] for _, f in worst_entries) / len(worst_entries)
    detail = (
        f"document_number {worst_value!r} appears on {doc_count} different documents in this "
        "bundle -- confirm this is expected (e.g. the same person's ID referenced on related "
        "paperwork) rather than one document's number copied onto another."
    )
    # Informational by default: reuse is common and often legitimate (a
    # person's own ID number appearing on several of their own documents),
    # so this warns rather than fails outright.
    return builder.result("warn", min(20.0 * doc_count, 60.0), avg_conf, detail)


# --------------------------------------------------------------------------- #
# date_ordering (per document)                                                #
# --------------------------------------------------------------------------- #


_DATE_ORDER_PAIRS = (
    ("issue_date", "expiry_date"),
    ("pay_period_start", "pay_period_end"),
    ("statement_period_start", "statement_period_end"),
)


def _check_date_ordering(
    documents: list[Document], extractions: list[Extraction]
) -> tuple[ConsistencyCheck, ConsistencyCrossRef | None]:
    check_id, label = "date_ordering", "Date fields are in a sensible order"
    builder = _CheckBuilder(id=check_id, label=label, field=None)

    violations: list[str] = []
    pairs_checked = 0
    confidences: list[float] = []

    for doc, extraction in zip(documents, extractions):
        for start_key, end_key in _DATE_ORDER_PAIRS:
            start_f = _best_value(extraction, start_key)
            end_f = _best_value(extraction, end_key)
            if not start_f or not end_f:
                continue
            start_v, end_v = start_f["value_normalized"], end_f["value_normalized"]
            if not start_v or not end_v:
                continue
            pairs_checked += 1
            confidences.append(min(start_f["confidence"], end_f["confidence"]))
            builder.observe(doc["id"], f"{start_key}={start_v}")
            builder.observe(doc["id"], f"{end_key}={end_v}")
            if start_v > end_v:  # ISO YYYY-MM-DD sorts lexicographically
                violations.append(f"{doc['id']}: {start_key} ({start_v}) is after {end_key} ({end_v})")

    if pairs_checked == 0:
        return (
            _not_applicable(
                check_id, label, None,
                "No document has both ends of a date range (issue/expiry, period start/end).",
            ),
            None,
        )

    avg_conf = sum(confidences) / len(confidences)
    if violations:
        return builder.result(
            "fail",
            min(30.0 * len(violations), 90.0),
            avg_conf,
            "Out-of-order date range(s): " + "; ".join(violations),
        )
    return builder.result(
        "pass", 0.0, avg_conf,
        f"All {pairs_checked} date range(s) checked are in order (start before end).",
    )


# --------------------------------------------------------------------------- #
# amount_arithmetic (per document)                                            #
# --------------------------------------------------------------------------- #


def _check_amount_arithmetic(
    documents: list[Document], extractions: list[Extraction]
) -> tuple[ConsistencyCheck, ConsistencyCrossRef | None]:
    check_id, label = "amount_arithmetic", "Gross / tax / net amounts reconcile"
    builder = _CheckBuilder(id=check_id, label=label, field=None)

    issues: list[str] = []
    checked = 0
    confidences: list[float] = []

    for doc, extraction in zip(documents, extractions):
        gross_f = _best_value(extraction, "gross_pay")
        net_f = _best_value(extraction, "net_pay")
        tax_f = _best_value(extraction, "tax")
        if not gross_f or not net_f:
            continue
        gross = _to_number(gross_f["value_normalized"] or gross_f["value"])
        net = _to_number(net_f["value_normalized"] or net_f["value"])
        if gross is None or net is None:
            continue
        checked += 1
        conf_bits = [gross_f["confidence"], net_f["confidence"]]
        builder.observe(doc["id"], f"gross_pay={gross}")
        builder.observe(doc["id"], f"net_pay={net}")

        tax = None
        if tax_f is not None:
            tax = _to_number(tax_f["value_normalized"] or tax_f["value"])
            if tax is not None:
                conf_bits.append(tax_f["confidence"])
                builder.observe(doc["id"], f"tax={tax}")

        confidences.append(sum(conf_bits) / len(conf_bits))

        if tax is not None:
            expected_net = gross - tax
            if gross != 0 and abs(expected_net - net) / max(abs(gross), 1.0) > _ARITHMETIC_TOLERANCE:
                issues.append(
                    f"{doc['id']}: gross ({gross}) - tax ({tax}) = {expected_net:.2f}, "
                    f"but net_pay is {net} -- off by {abs(expected_net - net):.2f}"
                )
        elif net > gross * (1 + _ARITHMETIC_TOLERANCE):
            issues.append(f"{doc['id']}: net_pay ({net}) exceeds gross_pay ({gross})")

    if checked == 0:
        return (
            _not_applicable(
                check_id, label, None,
                "No document has both gross_pay and net_pay to reconcile.",
            ),
            None,
        )

    avg_conf = sum(confidences) / len(confidences)
    if issues:
        return builder.result(
            "fail", min(35.0 * len(issues), 90.0), avg_conf,
            "Arithmetic does not reconcile: " + "; ".join(issues),
        )
    return builder.result(
        "pass", 0.0, avg_conf,
        f"Gross/net (and tax, where present) reconcile on all {checked} document(s) checked.",
    )


# --------------------------------------------------------------------------- #
# public entry point                                                          #
# --------------------------------------------------------------------------- #


def check_consistency(
    documents: list[Document],
    extractions: list[Extraction],
) -> Consistency:
    """Compare the extracted fields of every document in a bundle.

    Parameters
    ----------
    documents:
        All normalized documents in the bundle (contract §1), order-aligned
        with ``extractions``.
    extractions:
        The ``Extraction`` (contract §2) for each document, same order.

    Returns
    -------
    Consistency
        Contract §5. Every check is contract-valid; a check that had
        nothing to compare is reported ``not_applicable`` rather than
        omitted or guessed.
    """
    if len(documents) != len(extractions):
        raise ValueError(
            f"documents ({len(documents)}) and extractions ({len(extractions)}) must be order-aligned"
        )

    checks: list[ConsistencyCheck] = []
    cross_references: list[ConsistencyCrossRef] = []

    def add(pair: tuple[ConsistencyCheck, ConsistencyCrossRef | None]) -> None:
        check, crossref = pair
        checks.append(check)
        if crossref is not None:
            cross_references.append(crossref)

    if len(documents) < 2:
        summary = (
            "Only one document in this bundle -- nothing to cross-check."
            if documents
            else "No documents in this bundle."
        )
        checks = [
            _not_applicable("name_match", "Name matches across documents", "full_name", summary),
            _not_applicable("dob_match", "Date of birth matches across documents", "date_of_birth", summary),
            _not_applicable("address_match", "Address matches across documents", "address", summary),
            _not_applicable(
                "document_number_reuse", "Document number reused across documents", "document_number", summary
            ),
            _not_applicable("date_ordering", "Date fields are in a sensible order", None, summary),
            _not_applicable("amount_arithmetic", "Gross / tax / net amounts reconcile", None, summary),
        ]
        return Consistency(
            engine=ENGINE, engine_version=ENGINE_VERSION, checks=checks,
            cross_references=[], score=0.0, summary=summary,
        )

    add(_check_field_agreement(
        "name_match", "Name matches across documents", "full_name",
        documents, extractions, exact_only=False,
    ))
    add(_check_field_agreement(
        "dob_match", "Date of birth matches across documents", "date_of_birth",
        documents, extractions, exact_only=True,
    ))
    add(_check_field_agreement(
        "address_match", "Address matches across documents", "address",
        documents, extractions, exact_only=False,
    ))
    add(_check_document_number_reuse(documents, extractions))
    add(_check_date_ordering(documents, extractions))
    add(_check_amount_arithmetic(documents, extractions))

    applicable = [c for c in checks if c["status"] != "not_applicable"]
    # Rolled up as the worst applicable finding, not an average: in a fraud
    # review tool, five clean checks should not dilute one real conflict.
    score = max((c["score"] for c in applicable), default=0.0)

    failed = [c["label"] for c in checks if c["status"] == "fail"]
    warned = [c["label"] for c in checks if c["status"] == "warn"]
    if failed:
        summary = f"{len(failed)} check(s) failed: " + "; ".join(failed) + "."
    elif warned:
        summary = f"No failures; {len(warned)} check(s) warrant a second look: " + "; ".join(warned) + "."
    elif applicable:
        summary = f"All {len(applicable)} applicable check(s) passed."
    else:
        summary = "No fields were present on more than one document to compare."

    return Consistency(
        engine=ENGINE,
        engine_version=ENGINE_VERSION,
        checks=checks,
        cross_references=cross_references,
        score=round(score, 2),
        summary=summary,
    )
