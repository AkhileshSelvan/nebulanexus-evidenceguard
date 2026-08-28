"""Unit tests for ``modules.ocr.fields.extract_fields`` against plain text --
no image/OCR involved, so these are fast and pin down the parsing logic
precisely.
"""

from __future__ import annotations

from modules.ocr.fields import extract_fields


def test_labelled_date_of_birth_is_normalized_to_iso():
    text = "Date of Birth: 15 July 1998\n"
    result = extract_fields(text, [])
    dob = [f for f in result.fields if f["key"] == "date_of_birth"]
    assert dob, result.fields
    assert dob[0]["value_normalized"] == "1998-07-15"
    # No OCR word confidence was supplied (empty ``words``), so this floors
    # at _MIN_OCR_CONF_FLOOR * the labelled-cue strength -- still comfortably
    # above an unlabelled/pattern-only match.
    assert dob[0]["confidence"] > 0.3


def test_document_number_after_label():
    text = "Certificate Number: CERT-2024-00981\n"
    result = extract_fields(text, [])
    nums = [f for f in result.fields if f["key"] == "document_number"]
    assert nums, result.fields
    assert "CERT" in nums[0]["value"]


def test_money_field_picks_correct_key_from_line_label():
    text = "Gross Pay: $4,500.00\nNet Pay: $3,800.50\n"
    result = extract_fields(text, [])
    keys = {f["key"]: f["value_normalized"] for f in result.fields}
    assert keys.get("gross_pay") == "4500.00"
    assert keys.get("net_pay") == "3800.50"


def test_money_field_does_not_truncate_ungrouped_amounts():
    # Regression: an amount with no thousands separator (e.g. "45000.00",
    # common in OCR'd payslips) was being truncated to just its first 3
    # digits ("450") by a regex alternation bug. See fields.py _MONEY.
    text = "Net Pay: Rs. 45000.00\n"
    result = extract_fields(text, [])
    net = [f for f in result.fields if f["key"] == "net_pay"]
    assert net, result.fields
    assert net[0]["value_normalized"] == "45000.00"
    assert "45000.00" in net[0]["value"]


def test_money_field_handles_indian_lakh_grouping():
    text = "Total: Rs. 4,50,000.00\n"
    result = extract_fields(text, [])
    total = [f for f in result.fields if f["key"] == "total"]
    assert total, result.fields
    assert total[0]["value_normalized"] == "450000.00"


def test_score_field_with_percentage():
    text = "Overall Score: 87%\n"
    result = extract_fields(text, [])
    scores = [f for f in result.fields if f["key"] == "score"]
    assert scores, result.fields
    assert scores[0]["value_normalized"] == "87"


def test_no_fabricated_fields_on_empty_text():
    result = extract_fields("", [])
    assert result.fields == []
    assert result.warnings == []


def test_no_fabricated_fields_on_irrelevant_text():
    result = extract_fields("The quick brown fox jumps over the lazy dog.", [])
    # No labels, no date patterns, no money -- nothing should be invented.
    assert result.fields == []


def test_duplicate_value_keeps_higher_confidence_only():
    text = "Date of Birth: 01/02/2000\nDate of Birth: 01/02/2000\n"
    result = extract_fields(text, [])
    dob = [f for f in result.fields if f["key"] == "date_of_birth"]
    # Same (key, normalized value) seen twice on one page should not duplicate.
    assert len(dob) == 1


def test_low_confidence_field_gets_a_warning():
    # "name" alone (no stronger cue like "full name") is a weak match.
    text = "Name John Smith Extra Words Here\n"
    result = extract_fields(text, [])
    weak = [f for f in result.fields if f["key"] == "full_name" and f["confidence"] < 0.5]
    if weak:
        assert any("low-confidence" in w for w in result.warnings)
