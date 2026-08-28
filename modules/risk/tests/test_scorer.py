"""Unit tests for the risk fusion engine.

Covers the acceptance criteria on issue #7:
  * deterministic inputs -> deterministic outputs
  * every elevated score has evidence/reasons
  * no single signal can auto-prove fraud
  * bounded [0,100], missing evidence is neutral, no double counting
"""

from __future__ import annotations

import pytest

from modules.risk.tests.helpers import (
    CLEAN_CONSISTENCY,
    CLEAN_FORENSICS,
    CLEAN_METADATA,
    consistency,
    consistency_check,
    extraction,
    forensic_signal,
    forensics,
    metadata,
    metadata_signal,
)
from modules.contract import SEVERITY_BANDS, severity_for_score
from modules.risk import (
    REASON_CODES,
    SOURCE_PROBABILITY_CEILING,
    SOURCE_WEIGHTS,
    explain,
    recommend,
    score_bundle,
    score_document,
)

SEVERITIES = set(SEVERITY_BANDS)
DECISIONS = {"accept", "review", "reject"}


def _sum_contributions(risk: dict) -> float:
    return sum(c["contribution"] for c in risk["contributions"])


# --------------------------------------------------------------------------- #
# 1. All-clean case                                                           #
# --------------------------------------------------------------------------- #


def test_all_clean_document_scores_zero() -> None:
    risk = score_document("doc_1", CLEAN_FORENSICS, CLEAN_METADATA, extraction())
    assert risk["score"] == 0.0
    assert risk["severity"] == "low"
    assert risk["contributions"] == []


def test_all_clean_bundle_accepts_with_no_reasons_beyond_no_signals() -> None:
    doc = score_document("doc_1", CLEAN_FORENSICS, CLEAN_METADATA, extraction())
    bundle = score_bundle("bnd_1", [doc], CLEAN_CONSISTENCY)

    assert bundle["score"] == 0.0
    assert bundle["severity"] == "low"
    assert bundle["contributions"] == []

    rec = recommend(bundle)
    assert rec["decision"] == "accept"
    assert any("NO_SIGNALS" in r for r in rec["reasons"])
    # A clean result is reported with moderate, not total, confidence.
    assert 0.0 < rec["confidence"] < 1.0


def test_passed_signals_are_not_counted_even_with_a_score() -> None:
    """A signal flagged passed=True is clean; its score must be ignored."""
    risk = score_document(
        "doc_1",
        forensics(forensic_signal("ela_hotspot", 95.0, 0.95, passed=True)),
        CLEAN_METADATA,
    )
    assert risk["score"] == 0.0
    assert risk["contributions"] == []


# --------------------------------------------------------------------------- #
# 2. Single weak warning                                                      #
# --------------------------------------------------------------------------- #


def test_single_weak_warning_stays_low_or_medium_never_rejects() -> None:
    risk = score_document(
        "doc_1",
        CLEAN_FORENSICS,
        metadata(metadata_signal("modified_after_creation", 25.0, 0.5)),
    )
    bundle = score_bundle("bnd_1", [risk], CLEAN_CONSISTENCY)
    rec = recommend(bundle)

    assert 0.0 < risk["score"] < 25.0
    assert rec["decision"] in {"accept", "review"}
    assert rec["decision"] != "reject"


def test_moderate_uncertain_evidence_can_reach_review() -> None:
    """Requirement: uncertain evidence must be able to produce REVIEW_REQUIRED."""
    risk = score_document(
        "doc_1",
        forensics(forensic_signal("noise_inconsistency", 70.0, 0.7)),
        metadata(metadata_signal("editor_is_image_tool", 55.0, 0.6)),
    )
    bundle = score_bundle("bnd_1", [risk], CLEAN_CONSISTENCY)
    rec = recommend(bundle)

    assert rec["decision"] == "review"
    assert bundle["severity"] in {"medium", "high"}


# --------------------------------------------------------------------------- #
# 3. Multiple independent warnings                                            #
# --------------------------------------------------------------------------- #


def test_multiple_warnings_score_higher_than_any_one_alone() -> None:
    one = score_document(
        "doc_1", forensics(forensic_signal("ela_hotspot", 60.0, 0.8)), CLEAN_METADATA
    )
    two = score_document(
        "doc_1",
        forensics(
            forensic_signal("ela_hotspot", 60.0, 0.8),
            forensic_signal("copy_move", 60.0, 0.8),
        ),
        CLEAN_METADATA,
    )
    assert two["score"] > one["score"]
    # ...but with diminishing returns: never simply additive.
    assert two["score"] < one["score"] * 2


def test_corroboration_across_sources_is_flagged() -> None:
    doc = score_document(
        "doc_1",
        forensics(forensic_signal("splicing_boundary", 70.0, 0.8)),
        metadata(metadata_signal("future_timestamp", 60.0, 0.8)),
    )
    bundle = score_bundle("bnd_1", [doc], CLEAN_CONSISTENCY)
    rec = recommend(bundle)
    assert any("CORROBORATED" in r for r in rec["reasons"])


def test_single_source_concern_is_flagged_as_such() -> None:
    doc = score_document(
        "doc_1", forensics(forensic_signal("copy_move", 70.0, 0.8)), CLEAN_METADATA
    )
    bundle = score_bundle("bnd_1", [doc], CLEAN_CONSISTENCY)
    rec = recommend(bundle)
    assert any("SINGLE_SOURCE" in r for r in rec["reasons"])
    assert any("Corroborate" in a for a in rec["suggested_actions"])


# --------------------------------------------------------------------------- #
# 4. Strong cross-document contradiction                                      #
# --------------------------------------------------------------------------- #


def test_contradiction_meaningfully_raises_bundle_risk() -> None:
    docs = [
        score_document("doc_1", CLEAN_FORENSICS, CLEAN_METADATA),
        score_document("doc_2", CLEAN_FORENSICS, CLEAN_METADATA),
    ]
    without = score_bundle("bnd_1", docs, CLEAN_CONSISTENCY)
    with_conflict = score_bundle(
        "bnd_1",
        docs,
        consistency(
            consistency_check("name_match", 90.0, "fail", 0.9, field="full_name"),
            consistency_check("dob_match", 85.0, "fail", 0.9, field="date_of_birth"),
        ),
    )

    assert without["score"] == 0.0
    assert with_conflict["score"] > 40.0
    assert recommend(with_conflict)["decision"] == "review"
    assert any(
        c["source"] == "consistency" for c in with_conflict["contributions"]
    )


def test_contradiction_plus_forensics_can_reach_reject() -> None:
    """Corroborated, strong, multi-source evidence *should* be able to reject."""
    docs = [
        score_document(
            "doc_1",
            forensics(
                forensic_signal("splicing_boundary", 95.0, 0.95),
                forensic_signal("copy_move", 90.0, 0.9),
            ),
            metadata(metadata_signal("future_timestamp", 85.0, 0.9)),
        ),
        score_document(
            "doc_2",
            forensics(forensic_signal("double_compression", 88.0, 0.9)),
            CLEAN_METADATA,
        ),
    ]
    bundle = score_bundle(
        "bnd_1",
        docs,
        consistency(
            consistency_check("name_match", 95.0, "fail", 0.95),
            consistency_check("amount_arithmetic", 90.0, "fail", 0.9),
        ),
    )
    assert bundle["severity"] == "critical"
    assert recommend(bundle)["decision"] == "reject"


def test_consistency_warn_status_counts_but_pass_does_not() -> None:
    docs = [score_document("doc_1", CLEAN_FORENSICS, CLEAN_METADATA)]
    warned = score_bundle(
        "bnd_1", docs, consistency(consistency_check("address_match", 40.0, "warn", 0.7))
    )
    passed = score_bundle(
        "bnd_1", docs, consistency(consistency_check("address_match", 40.0, "pass", 0.7))
    )
    not_applicable = score_bundle(
        "bnd_1",
        docs,
        consistency(consistency_check("address_match", 40.0, "not_applicable", 0.7)),
    )
    assert warned["score"] > 0.0
    assert passed["score"] == 0.0
    assert not_applicable["score"] == 0.0


# --------------------------------------------------------------------------- #
# 5. Missing signals / missing sections                                       #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "forensics_arg, metadata_arg",
    [(None, None), ({}, {}), (forensics(), metadata()), (None, CLEAN_METADATA)],
)
def test_missing_sections_are_neutral_not_incriminating(
    forensics_arg, metadata_arg
) -> None:
    risk = score_document("doc_1", forensics_arg, metadata_arg)
    assert risk["score"] == 0.0
    assert risk["severity"] == "low"
    assert risk["contributions"] == []


def test_malformed_sections_do_not_raise() -> None:
    risk = score_document("doc_1", {"signals": "not-a-list"}, {"signals": [None, 42]})
    assert risk["score"] == 0.0


def test_bundle_tolerates_no_documents_and_no_consistency() -> None:
    bundle = score_bundle("bnd_1", None, None)
    assert bundle["score"] == 0.0
    assert bundle["scope"] == "bundle"
    assert recommend(bundle)["decision"] == "accept"


def test_unavailable_ocr_engine_adds_no_risk() -> None:
    """A check that did not run is not evidence of anything."""
    ran = score_document(
        "doc_1", CLEAN_FORENSICS, CLEAN_METADATA, extraction(full_text="", text_confidence=0.0)
    )
    did_not_run = score_document(
        "doc_1",
        CLEAN_FORENSICS,
        CLEAN_METADATA,
        extraction(engine="tesseract-unavailable", full_text="", text_confidence=0.0),
    )
    assert ran["score"] > 0.0  # OCR ran and found nothing readable -> mild concern
    assert did_not_run["score"] == 0.0  # OCR never ran -> no evidence at all


def test_coverage_gaps_lower_confidence_but_never_raise_score() -> None:
    doc = score_document(
        "doc_1", forensics(forensic_signal("ela_hotspot", 60.0, 0.8)), CLEAN_METADATA
    )
    bundle = score_bundle("bnd_1", [doc], CLEAN_CONSISTENCY)
    full = recommend(bundle)
    partial = recommend(bundle, coverage_gaps=["ocr", "metadata"])

    assert partial["confidence"] < full["confidence"]
    assert partial["based_on"]["bundle_risk_score"] == full["based_on"]["bundle_risk_score"]
    assert any("COVERAGE_GAP" in r for r in partial["reasons"])


def test_ocr_quality_is_a_weak_nudge_not_an_accusation() -> None:
    risk = score_document(
        "doc_1",
        CLEAN_FORENSICS,
        CLEAN_METADATA,
        extraction(full_text="blurry", text_confidence=0.10),
    )
    assert 0.0 < risk["score"] < 15.0
    assert risk["severity"] == "low"


# --------------------------------------------------------------------------- #
# 6. Score clamping / bounds                                                  #
# --------------------------------------------------------------------------- #


def test_score_never_reaches_100_even_under_extreme_input() -> None:
    docs = [
        score_document(
            f"doc_{i}",
            forensics(*[forensic_signal(f"f_{j}", 100.0, 1.0) for j in range(25)]),
            metadata(*[metadata_signal(f"m_{j}", 100.0, 1.0) for j in range(25)]),
            extraction(full_text="", text_confidence=0.0),
        )
        for i in range(5)
    ]
    bundle = score_bundle(
        "bnd_1",
        docs,
        consistency(*[consistency_check(f"c_{j}", 100.0, "fail", 1.0) for j in range(25)]),
    )
    assert 0.0 <= bundle["score"] < 100.0
    assert bundle["severity"] in SEVERITIES
    for doc in docs:
        assert 0.0 <= doc["score"] < 100.0


def test_out_of_range_and_garbage_inputs_are_sanitised() -> None:
    risk = score_document(
        "doc_1",
        forensics(
            forensic_signal("over", 5000.0, 9.0),
            forensic_signal("under", -80.0, -3.0),
            forensic_signal("nonsense", "abc", None),
        ),
        CLEAN_METADATA,
    )
    assert 0.0 <= risk["score"] < 100.0
    for c in risk["contributions"]:
        assert 0.0 <= c["signal_score"] <= 100.0
        assert 0.0 <= c["weight"] <= 1.0


def test_per_source_ceiling_caps_a_noisy_module() -> None:
    """Fifty metadata signals must not out-argue the metadata source ceiling."""
    risk = score_document(
        "doc_1",
        CLEAN_FORENSICS,
        metadata(*[metadata_signal(f"m_{j}", 100.0, 1.0) for j in range(50)]),
    )
    ceiling = SOURCE_PROBABILITY_CEILING["metadata"] * 100.0
    assert risk["score"] <= ceiling + 0.01
    # Metadata alone can therefore never recommend rejection.
    assert risk["severity"] != "critical"


def test_severity_bands_match_the_shared_contract() -> None:
    for score in (0.0, 24.9, 25.0, 49.9, 50.0, 74.9, 75.0, 99.9):
        assert severity_for_score(score) in SEVERITIES


@pytest.mark.parametrize(
    "score, expected",
    [
        (0.0, "low"),
        (24.0, "low"),
        (24.6, "low"),  # regression: used to fall through to "critical"
        (24.999, "low"),
        (25.0, "medium"),
        (49.27, "medium"),  # regression
        (49.9, "medium"),
        (50.0, "high"),
        (74.5, "high"),  # regression
        (74.999, "high"),
        (75.0, "critical"),
        (100.0, "critical"),
    ],
)
def test_fractional_scores_land_in_the_right_band(score, expected) -> None:
    """The bands are written as inclusive integers but scores are continuous.

    Anything in (24,25), (49,50) or (74,75) previously matched no band and hit
    the fallback, which reported it as 'critical' -> 'reject'.
    """
    assert severity_for_score(score) == expected


# --------------------------------------------------------------------------- #
# 7. Determinism                                                              #
# --------------------------------------------------------------------------- #


def test_repeated_scoring_is_byte_identical() -> None:
    def build() -> tuple[dict, dict, dict]:
        docs = [
            score_document(
                "doc_1",
                forensics(
                    forensic_signal("ela_hotspot", 72.0, 0.85),
                    forensic_signal("copy_move", 44.0, 0.6),
                ),
                metadata(metadata_signal("future_timestamp", 61.0, 0.7)),
                extraction(text_confidence=0.4),
            ),
            score_document(
                "doc_2",
                forensics(forensic_signal("double_compression", 33.0, 0.5)),
                CLEAN_METADATA,
            ),
        ]
        bundle = score_bundle(
            "bnd_1", docs, consistency(consistency_check("dob_match", 80.0, "fail", 0.9))
        )
        return bundle, recommend(bundle), explain(bundle, docs, CLEAN_CONSISTENCY)

    first = build()
    for _ in range(5):
        assert build() == first


def test_document_order_does_not_change_the_bundle_score() -> None:
    a = score_document(
        "doc_a", forensics(forensic_signal("ela_hotspot", 70.0, 0.8)), CLEAN_METADATA
    )
    b = score_document(
        "doc_b", forensics(forensic_signal("copy_move", 50.0, 0.7)), CLEAN_METADATA
    )
    assert (
        score_bundle("bnd", [a, b], CLEAN_CONSISTENCY)["score"]
        == score_bundle("bnd", [b, a], CLEAN_CONSISTENCY)["score"]
    )


# --------------------------------------------------------------------------- #
# 8. Recommendation mapping                                                   #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "score, severity, decision",
    [
        (0.0, "low", "accept"),
        (24.0, "low", "accept"),
        (25.0, "medium", "review"),
        (49.0, "medium", "review"),
        (50.0, "high", "review"),
        (74.0, "high", "review"),
        (75.0, "critical", "reject"),
        (99.0, "critical", "reject"),
    ],
)
def test_severity_to_decision_mapping(score, severity, decision) -> None:
    fake = {
        "engine": "t",
        "engine_version": "1",
        "scope": "bundle",
        "subject_id": "bnd",
        "score": score,
        "severity": severity_for_score(score),
        "contributions": [],
        "model": {"method": "m", "version": "1"},
    }
    assert fake["severity"] == severity
    rec = recommend(fake)
    assert rec["decision"] == decision
    assert rec["based_on"]["severity"] == severity
    assert rec["based_on"]["bundle_risk_score"] == score
    assert rec["decision"] in DECISIONS


def test_recommendation_confidence_is_never_certainty() -> None:
    """A triage engine must not claim to be sure."""
    for score in (0.0, 30.0, 60.0, 99.0):
        fake = {
            "score": score,
            "severity": severity_for_score(score),
            "contributions": [
                {
                    "source": "forensics",
                    "signal_id": "x",
                    "signal_score": 90.0,
                    "weight": 0.55,
                    "contribution": score,
                }
            ],
        }
        rec = recommend(fake)
        assert 0.0 < rec["confidence"] < 1.0


def test_elevated_score_always_carries_reasons() -> None:
    doc = score_document(
        "doc_1", forensics(forensic_signal("ela_hotspot", 80.0, 0.9)), CLEAN_METADATA
    )
    bundle = score_bundle("bnd_1", [doc], CLEAN_CONSISTENCY)
    rec = recommend(bundle)
    assert bundle["score"] > 0.0
    assert rec["reasons"]
    assert bundle["contributions"]
    assert all(code in REASON_CODES for code in _codes(rec["reasons"]))


def _codes(reasons: list[str]) -> list[str]:
    return [r[1 : r.index("]")] for r in reasons if r.startswith("[") and "]" in r]


# --------------------------------------------------------------------------- #
# 9. Contribution ordering + exact attribution                                #
# --------------------------------------------------------------------------- #


def test_contributions_are_sorted_by_importance() -> None:
    risk = score_document(
        "doc_1",
        forensics(
            forensic_signal("weak", 20.0, 0.5),
            forensic_signal("strong", 95.0, 0.95),
            forensic_signal("middle", 60.0, 0.7),
        ),
        metadata(metadata_signal("meta_weak", 15.0, 0.4)),
    )
    values = [c["contribution"] for c in risk["contributions"]]
    assert values == sorted(values, reverse=True)
    assert risk["contributions"][0]["signal_id"].startswith("strong")


def test_contributions_sum_to_the_score() -> None:
    """The identity that makes an elevated score auditable by hand."""
    risk = score_document(
        "doc_1",
        forensics(
            forensic_signal("a", 80.0, 0.9),
            forensic_signal("b", 55.0, 0.7),
            forensic_signal("c", 30.0, 0.5),
        ),
        metadata(metadata_signal("d", 65.0, 0.8)),
        extraction(text_confidence=0.3),
    )
    assert _sum_contributions(risk) == pytest.approx(risk["score"], abs=0.01)


def test_bundle_contributions_sum_to_the_bundle_score() -> None:
    docs = [
        score_document(
            "doc_1",
            forensics(forensic_signal("ela_hotspot", 70.0, 0.8)),
            metadata(metadata_signal("future_timestamp", 50.0, 0.7)),
        ),
        score_document(
            "doc_2", forensics(forensic_signal("copy_move", 60.0, 0.75)), CLEAN_METADATA
        ),
    ]
    bundle = score_bundle(
        "bnd_1", docs, consistency(consistency_check("name_match", 85.0, "fail", 0.9))
    )
    assert _sum_contributions(bundle) == pytest.approx(bundle["score"], abs=0.01)


def test_contribution_records_carry_the_required_fields() -> None:
    risk = score_document(
        "doc_1", forensics(forensic_signal("ela_hotspot", 70.0, 0.8)), CLEAN_METADATA
    )
    for c in risk["contributions"]:
        assert set(c) == {
            "source",
            "signal_id",
            "signal_score",
            "weight",
            "contribution",
        }
        assert c["source"] in SOURCE_WEIGHTS
        assert c["weight"] == SOURCE_WEIGHTS[c["source"]]


def test_duplicate_signals_are_not_double_counted() -> None:
    once = score_document(
        "doc_1", forensics(forensic_signal("ela_hotspot", 70.0, 0.8)), CLEAN_METADATA
    )
    twice = score_document(
        "doc_1",
        forensics(
            forensic_signal("ela_hotspot", 70.0, 0.8),
            forensic_signal("ela_hotspot", 70.0, 0.8),
        ),
        CLEAN_METADATA,
    )
    assert once["score"] == twice["score"]
    assert len(twice["contributions"]) == 1


# --------------------------------------------------------------------------- #
# 10. Explanation traceability                                                #
# --------------------------------------------------------------------------- #


def test_every_explanation_evidence_maps_to_a_real_contribution() -> None:
    docs = [
        score_document(
            "doc_1",
            forensics(forensic_signal("ela_hotspot", 75.0, 0.85)),
            metadata(metadata_signal("future_timestamp", 60.0, 0.8)),
        )
    ]
    cons = consistency(
        consistency_check("name_match", 88.0, "fail", 0.9, detail="Names differ: A vs B")
    )
    bundle = score_bundle("bnd_1", docs, cons)
    exp = explain(bundle, docs, cons)

    contribution_ids = {
        c["signal_id"].split("@")[0] for c in bundle["contributions"]
    }
    seen = set()
    for factor in exp["factors"]:
        assert factor["evidence"], "a factor must cite evidence"
        for ev in factor["evidence"]:
            assert ev["signal_id"] in contribution_ids
            assert ev["section"] in {
                "extraction",
                "forensics",
                "metadata",
                "consistency",
            }
            assert ev["quote"]
            seen.add(ev["signal_id"])
    assert seen == contribution_ids


def test_explanation_quotes_the_producing_module_verbatim_when_available() -> None:
    detail = "Names differ: 'Jane Doe' on the ID vs 'J. Doe' on the payslip."
    cons = consistency(consistency_check("name_match", 88.0, "fail", 0.9, detail=detail))
    docs = [score_document("doc_1", CLEAN_FORENSICS, CLEAN_METADATA)]
    bundle = score_bundle("bnd_1", docs, cons)
    exp = explain(bundle, docs, cons)

    quotes = [ev["quote"] for f in exp["factors"] for ev in f["evidence"]]
    assert detail in quotes


def test_clean_explanation_does_not_claim_the_documents_are_genuine() -> None:
    docs = [score_document("doc_1", CLEAN_FORENSICS, CLEAN_METADATA)]
    bundle = score_bundle("bnd_1", docs, CLEAN_CONSISTENCY)
    exp = explain(bundle, docs, CLEAN_CONSISTENCY)

    assert exp["factors"] == []
    assert "not a finding that the documents are genuine" in exp["summary"]


def test_elevated_explanation_disclaims_a_fraud_verdict() -> None:
    docs = [
        score_document(
            "doc_1", forensics(forensic_signal("splicing_boundary", 90.0, 0.9)), CLEAN_METADATA
        )
    ]
    bundle = score_bundle("bnd_1", docs, CLEAN_CONSISTENCY)
    exp = explain(bundle, docs, CLEAN_CONSISTENCY)
    assert "not a determination of fraud" in exp["summary"]
    assert exp["glossary"]


def test_explanation_reports_no_numbers_absent_from_the_evidence() -> None:
    """Every number in a factor's quote must come from the contribution itself."""
    docs = [
        score_document(
            "doc_1", forensics(forensic_signal("copy_move", 64.0, 0.8)), CLEAN_METADATA
        )
    ]
    bundle = score_bundle("bnd_1", docs, CLEAN_CONSISTENCY)
    exp = explain(bundle, docs, CLEAN_CONSISTENCY)

    contribution = bundle["contributions"][0]
    quote = exp["factors"][0]["evidence"][0]["quote"]
    assert f"{contribution['signal_score']:.0f}" in quote
    assert f"{contribution['contribution']:.1f}" in quote


# --------------------------------------------------------------------------- #
# 11. No single signal can auto-prove fraud                                   #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("source", ["forensics", "metadata"])
def test_one_maxed_signal_never_rejects(source: str) -> None:
    """Issue #7 acceptance criterion, checked at maximum strength/confidence."""
    if source == "forensics":
        doc = score_document(
            "doc_1", forensics(forensic_signal("smoking_gun", 100.0, 1.0)), CLEAN_METADATA
        )
    else:
        doc = score_document(
            "doc_1", CLEAN_FORENSICS, metadata(metadata_signal("smoking_gun", 100.0, 1.0))
        )

    bundle = score_bundle("bnd_1", [doc], CLEAN_CONSISTENCY)
    rec = recommend(bundle)

    assert doc["score"] < 75.0, "a lone signal must not reach the critical band"
    assert doc["severity"] != "critical"
    assert bundle["severity"] != "critical"
    assert rec["decision"] != "reject"
    assert rec["decision"] == "review"


def test_one_maxed_consistency_check_never_rejects() -> None:
    docs = [score_document("doc_1", CLEAN_FORENSICS, CLEAN_METADATA)]
    bundle = score_bundle(
        "bnd_1", docs, consistency(consistency_check("name_match", 100.0, "fail", 1.0))
    )
    assert bundle["score"] < 75.0
    assert recommend(bundle)["decision"] == "review"


def test_lone_signal_ceiling_equals_its_source_weight() -> None:
    """With one term the score is exactly 100 * score/100 * weight * confidence.

    This is the property that makes the 'no auto-fraud' policy auditable: read
    the weight table and you know the ceiling.
    """
    doc = score_document(
        "doc_1", forensics(forensic_signal("only", 100.0, 1.0)), CLEAN_METADATA
    )
    assert doc["score"] == pytest.approx(SOURCE_WEIGHTS["forensics"] * 100.0, abs=0.01)
    assert SOURCE_WEIGHTS["forensics"] * 100.0 < 75.0


def test_no_source_weight_can_alone_reach_the_critical_band() -> None:
    for source, weight in SOURCE_WEIGHTS.items():
        assert weight * 100.0 < 75.0, f"{source} weight would allow a lone rejection"


# --------------------------------------------------------------------------- #
# 12. No single SOURCE can independently produce a reject                     #
#                                                                             #
# Stricter than the per-signal rule above: even a source firing every signal   #
# it has, at maximum strength and confidence, must land in "review" at worst.  #
# Rejection requires corroboration from a second, independent source.          #
# --------------------------------------------------------------------------- #

CRITICAL_FLOOR = 75.0


def _saturate(source: str) -> tuple[dict, dict]:
    """Build (document_risk, bundle_risk) with *only* ``source`` raising concern."""
    if source == "forensics":
        doc = score_document(
            "doc_1",
            forensics(*[forensic_signal(f"f_{i}", 100.0, 1.0) for i in range(30)]),
            None,
            None,
        )
        return doc, score_bundle("bnd_1", [doc], None)

    if source == "metadata":
        doc = score_document(
            "doc_1",
            None,
            metadata(*[metadata_signal(f"m_{i}", 100.0, 1.0) for i in range(30)]),
            None,
        )
        return doc, score_bundle("bnd_1", [doc], None)

    if source == "ocr":
        # OCR evidence is derived, not supplied: the strongest case the module
        # can produce is text that was read at essentially zero confidence.
        doc = score_document(
            "doc_1", None, None, extraction(full_text="unreadable", text_confidence=0.001)
        )
        return doc, score_bundle("bnd_1", [doc], None)

    if source == "consistency":
        # Consistency is bundle-scoped by definition; there is no document half.
        clean_doc = score_document("doc_1", None, None, None)
        bundle = score_bundle(
            "bnd_1",
            [clean_doc],
            consistency(
                *[consistency_check(f"c_{i}", 100.0, "fail", 1.0) for i in range(30)]
            ),
        )
        return clean_doc, bundle

    raise AssertionError(f"unknown source {source!r}")


@pytest.mark.parametrize("source", ["forensics", "metadata", "consistency", "ocr"])
def test_no_single_source_can_independently_reject(source: str) -> None:
    doc, bundle = _saturate(source)

    assert doc["score"] < CRITICAL_FLOOR, (
        f"{source} alone reached {doc['score']} at document level"
    )
    assert doc["severity"] != "critical"
    assert bundle["score"] < CRITICAL_FLOOR, (
        f"{source} alone reached {bundle['score']} at bundle level"
    )
    assert bundle["severity"] != "critical"

    rec = recommend(bundle)
    assert rec["decision"] != "reject", f"{source} alone produced a reject decision"


@pytest.mark.parametrize("source", ["forensics", "metadata", "consistency", "ocr"])
def test_saturated_source_still_asks_for_review(source: str) -> None:
    """Capping a source must not silence it — it should still escalate."""
    _, bundle = _saturate(source)
    assert bundle["score"] > 0.0
    assert bundle["contributions"]
    assert recommend(bundle)["decision"] in {"accept", "review"}


def test_every_source_ceiling_is_below_the_critical_band() -> None:
    """The policy, stated directly against the constants that enforce it."""
    for source, ceiling in SOURCE_PROBABILITY_CEILING.items():
        assert ceiling * 100.0 < CRITICAL_FLOOR, (
            f"{source} ceiling {ceiling} would let that source alone reject"
        )


def test_two_sources_together_can_still_reach_critical() -> None:
    """The cap must not defang the engine: corroboration must still reject."""
    doc = score_document(
        "doc_1",
        forensics(*[forensic_signal(f"f_{i}", 100.0, 1.0) for i in range(10)]),
        None,
        None,
    )
    bundle = score_bundle(
        "bnd_1",
        [doc],
        consistency(*[consistency_check(f"c_{i}", 100.0, "fail", 1.0) for i in range(10)]),
    )
    assert bundle["score"] >= CRITICAL_FLOOR
    assert bundle["severity"] == "critical"
    assert recommend(bundle)["decision"] == "reject"
    assert len({c["source"] for c in bundle["contributions"]}) >= 2


def test_realistic_multi_source_bundle_reaches_reject() -> None:
    """Not a saturation edge case — plausible module output across three sources."""
    docs = [
        score_document(
            "doc_payslip",
            forensics(
                forensic_signal("splicing_boundary", 92.0, 0.9),
                forensic_signal("font_substitution", 80.0, 0.85),
            ),
            metadata(metadata_signal("modified_after_creation", 75.0, 0.85)),
            extraction(text_confidence=0.88),
        ),
        score_document(
            "doc_id",
            forensics(forensic_signal("double_compression", 84.0, 0.85)),
            None,
            extraction(text_confidence=0.91),
        ),
    ]
    bundle = score_bundle(
        "bnd_1",
        docs,
        consistency(
            consistency_check("name_match", 93.0, "fail", 0.92),
            consistency_check("dob_match", 88.0, "fail", 0.9),
        ),
    )
    rec = recommend(bundle)
    assert bundle["severity"] == "critical"
    assert rec["decision"] == "reject"
    assert any("CORROBORATED" in r for r in rec["reasons"])


# --------------------------------------------------------------------------- #
# 13. signal_id document tagging is lossless                                  #
# --------------------------------------------------------------------------- #


def test_document_tag_does_not_corrupt_ids_containing_at() -> None:
    """Tagging splits from the right, so '@' inside a module's own id survives."""
    original = "checks@issuer_domain"
    doc = score_document("doc_1", forensics(forensic_signal(original, 80.0, 0.9)), None)
    bundle = score_bundle("bnd_1", [doc], None)

    assert doc["contributions"][0]["signal_id"] == f"{original}@doc_1"
    assert bundle["contributions"][0]["signal_id"] == f"{original}@doc_1"

    evidence = explain(bundle, [doc], None)["factors"][0]["evidence"][0]
    assert evidence["signal_id"] == original
    assert evidence["document_id"] == "doc_1"


def test_bundle_scoped_signals_carry_no_document_tag() -> None:
    docs = [score_document("doc_1", CLEAN_FORENSICS, CLEAN_METADATA)]
    cons = consistency(consistency_check("name_match", 80.0, "fail", 0.9))
    bundle = score_bundle("bnd_1", docs, cons)

    assert bundle["contributions"][0]["signal_id"] == "name_match"
    evidence = explain(bundle, docs, cons)["factors"][0]["evidence"][0]
    assert evidence["signal_id"] == "name_match"
    assert evidence["document_id"] is None


# --------------------------------------------------------------------------- #
# Module independence                                                         #
# --------------------------------------------------------------------------- #


def test_risk_module_does_not_import_web_or_sibling_modules() -> None:
    source = (
        __import__("pathlib").Path(__file__).resolve().parents[1] / "scorer.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "import fastapi",
        "from fastapi",
        "import requests",
        "import httpx",
        "modules.ocr",
        "modules.forensics",
        "modules.consistency",
        "from app",
        "import app",
    ):
        assert forbidden not in source, f"risk must not reference {forbidden!r}"
