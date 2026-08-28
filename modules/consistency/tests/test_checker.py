"""Tests for modules.consistency.checker.check_consistency."""

from __future__ import annotations

from modules.consistency.checker import check_consistency

from .conftest import make_document, make_extraction, make_field


def _get(result, check_id):
    matches = [c for c in result["checks"] if c["id"] == check_id]
    assert matches, f"no check with id {check_id!r} in {[c['id'] for c in result['checks']]}"
    return matches[0]


# --------------------------------------------------------------------------- #
# baseline shape / edge cases                                                 #
# --------------------------------------------------------------------------- #


def test_empty_bundle_returns_all_not_applicable():
    result = check_consistency([], [])
    assert result["checks"]
    assert all(c["status"] == "not_applicable" for c in result["checks"])
    assert result["cross_references"] == []
    assert result["score"] == 0.0


def test_single_document_returns_all_not_applicable():
    doc = make_document("doc_1")
    extraction = make_extraction([make_field("full_name", "Jane Doe")])
    result = check_consistency([doc], [extraction])
    assert all(c["status"] == "not_applicable" for c in result["checks"])


def test_mismatched_lengths_raises():
    try:
        check_consistency([make_document("d1")], [])
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_result_shape_matches_contract():
    docs = [make_document("d1"), make_document("d2")]
    exts = [
        make_extraction([make_field("full_name", "Jane Doe")]),
        make_extraction([make_field("full_name", "Jane Doe")]),
    ]
    result = check_consistency(docs, exts)
    for key in ("engine", "engine_version", "checks", "cross_references", "score", "summary"):
        assert key in result
    for check in result["checks"]:
        for key in ("id", "label", "field", "status", "score", "confidence", "observed", "detail"):
            assert key in check
        assert check["status"] in ("pass", "warn", "fail", "not_applicable")
        assert 0.0 <= check["score"] <= 100.0
        assert 0.0 <= check["confidence"] <= 1.0
    for xref in result["cross_references"]:
        assert "check_id" in xref and "document_ids" in xref
        assert len(xref["document_ids"]) >= 2


# --------------------------------------------------------------------------- #
# name / dob / address agreement                                              #
# --------------------------------------------------------------------------- #


def test_identical_names_pass():
    docs = [make_document("d1"), make_document("d2")]
    exts = [
        make_extraction([make_field("full_name", "Jane Doe")]),
        make_extraction([make_field("full_name", "Jane Doe")]),
    ]
    result = check_consistency(docs, exts)
    assert _get(result, "name_match")["status"] == "pass"


def test_minor_name_variation_warns_not_fails():
    docs = [make_document("d1"), make_document("d2")]
    exts = [
        make_extraction([make_field("full_name", "Jane Doe")]),
        make_extraction([make_field("full_name", "Jane A. Doe")]),
    ]
    result = check_consistency(docs, exts)
    check = _get(result, "name_match")
    assert check["status"] == "warn"
    assert 0.0 < check["score"] < 100.0


def test_clearly_different_names_fail():
    docs = [make_document("d1"), make_document("d2")]
    exts = [
        make_extraction([make_field("full_name", "Jane Doe")]),
        make_extraction([make_field("full_name", "Robert Johnson")]),
    ]
    result = check_consistency(docs, exts)
    assert _get(result, "name_match")["status"] == "fail"


def test_dob_mismatch_fails_even_if_close():
    # DOB is exact-match-only: no "close enough" for a birth date.
    docs = [make_document("d1"), make_document("d2")]
    exts = [
        make_extraction([make_field("date_of_birth", "1998-07-15", normalized="1998-07-15")]),
        make_extraction([make_field("date_of_birth", "1998-07-16", normalized="1998-07-16")]),
    ]
    result = check_consistency(docs, exts)
    assert _get(result, "dob_match")["status"] == "fail"


def test_field_present_on_only_one_document_is_not_applicable():
    docs = [make_document("d1"), make_document("d2")]
    exts = [
        make_extraction([make_field("address", "12 Main St")]),
        make_extraction([]),  # no address on this one
    ]
    result = check_consistency(docs, exts)
    assert _get(result, "address_match")["status"] == "not_applicable"


# --------------------------------------------------------------------------- #
# document_number_reuse                                                       #
# --------------------------------------------------------------------------- #


def test_document_number_reused_across_documents_warns():
    docs = [make_document("d1"), make_document("d2")]
    exts = [
        make_extraction([make_field("document_number", "AB123456", normalized="AB123456")]),
        make_extraction([make_field("document_number", "AB123456", normalized="AB123456")]),
    ]
    result = check_consistency(docs, exts)
    check = _get(result, "document_number_reuse")
    assert check["status"] == "warn"
    xref = [x for x in result["cross_references"] if x["check_id"] == "document_number_reuse"]
    assert xref and set(xref[0]["document_ids"]) == {"d1", "d2"}


def test_distinct_document_numbers_not_applicable():
    docs = [make_document("d1"), make_document("d2")]
    exts = [
        make_extraction([make_field("document_number", "AB123456", normalized="AB123456")]),
        make_extraction([make_field("document_number", "ZZ999999", normalized="ZZ999999")]),
    ]
    result = check_consistency(docs, exts)
    assert _get(result, "document_number_reuse")["status"] == "not_applicable"


# --------------------------------------------------------------------------- #
# date_ordering                                                               #
# --------------------------------------------------------------------------- #


def test_issue_before_expiry_passes():
    docs = [make_document("d1"), make_document("d2")]
    exts = [
        make_extraction([
            make_field("issue_date", "2024-01-01", normalized="2024-01-01"),
            make_field("expiry_date", "2029-01-01", normalized="2029-01-01"),
        ]),
        make_extraction([]),
    ]
    result = check_consistency(docs, exts)
    assert _get(result, "date_ordering")["status"] == "pass"


def test_issue_after_expiry_fails():
    docs = [make_document("d1"), make_document("d2")]
    exts = [
        make_extraction([
            make_field("issue_date", "2029-01-01", normalized="2029-01-01"),
            make_field("expiry_date", "2024-01-01", normalized="2024-01-01"),
        ]),
        make_extraction([]),
    ]
    result = check_consistency(docs, exts)
    check = _get(result, "date_ordering")
    assert check["status"] == "fail"
    assert "d1" in check["detail"]


def test_no_date_pairs_present_is_not_applicable():
    docs = [make_document("d1"), make_document("d2")]
    exts = [make_extraction([]), make_extraction([])]
    result = check_consistency(docs, exts)
    assert _get(result, "date_ordering")["status"] == "not_applicable"


# --------------------------------------------------------------------------- #
# amount_arithmetic                                                           #
# --------------------------------------------------------------------------- #


def test_gross_minus_tax_equals_net_passes():
    docs = [make_document("d1"), make_document("d2")]
    exts = [
        make_extraction([
            make_field("gross_pay", "5000.00", normalized="5000.00"),
            make_field("tax", "500.00", normalized="500.00"),
            make_field("net_pay", "4500.00", normalized="4500.00"),
        ]),
        make_extraction([]),
    ]
    result = check_consistency(docs, exts)
    assert _get(result, "amount_arithmetic")["status"] == "pass"


def test_arithmetic_mismatch_fails():
    docs = [make_document("d1"), make_document("d2")]
    exts = [
        make_extraction([
            make_field("gross_pay", "5000.00", normalized="5000.00"),
            make_field("tax", "500.00", normalized="500.00"),
            make_field("net_pay", "3000.00", normalized="3000.00"),  # should be ~4500
        ]),
        make_extraction([]),
    ]
    result = check_consistency(docs, exts)
    check = _get(result, "amount_arithmetic")
    assert check["status"] == "fail"
    assert "d1" in check["detail"]


def test_net_exceeding_gross_without_tax_field_fails():
    docs = [make_document("d1"), make_document("d2")]
    exts = [
        make_extraction([
            make_field("gross_pay", "3000.00", normalized="3000.00"),
            make_field("net_pay", "5000.00", normalized="5000.00"),  # net > gross, no tax field
        ]),
        make_extraction([]),
    ]
    result = check_consistency(docs, exts)
    assert _get(result, "amount_arithmetic")["status"] == "fail"


def test_small_rounding_difference_within_tolerance_passes():
    docs = [make_document("d1"), make_document("d2")]
    exts = [
        make_extraction([
            make_field("gross_pay", "5000.00", normalized="5000.00"),
            make_field("tax", "500.00", normalized="500.00"),
            make_field("net_pay", "4500.05", normalized="4500.05"),  # 5 cent rounding
        ]),
        make_extraction([]),
    ]
    result = check_consistency(docs, exts)
    assert _get(result, "amount_arithmetic")["status"] == "pass"


# --------------------------------------------------------------------------- #
# bundle-level rollup                                                         #
# --------------------------------------------------------------------------- #


def test_bundle_score_reflects_worst_finding_not_average():
    docs = [make_document("d1"), make_document("d2")]
    exts = [
        make_extraction([
            make_field("full_name", "Jane Doe"),  # will pass
            make_field("date_of_birth", "1998-07-15", normalized="1998-07-15"),  # will fail
        ]),
        make_extraction([
            make_field("full_name", "Jane Doe"),
            make_field("date_of_birth", "1990-01-01", normalized="1990-01-01"),
        ]),
    ]
    result = check_consistency(docs, exts)
    dob = _get(result, "dob_match")
    assert dob["status"] == "fail"
    # bundle score must be at least as high as the worst single check --
    # a passing name_match must not dilute a failed dob_match.
    assert result["score"] >= dob["score"]


def test_three_documents_all_consistent():
    docs = [make_document("d1"), make_document("d2"), make_document("d3")]
    exts = [make_extraction([make_field("full_name", "Jane Doe")]) for _ in range(3)]
    result = check_consistency(docs, exts)
    check = _get(result, "name_match")
    assert check["status"] == "pass"
    assert len(check["observed"]) == 3
