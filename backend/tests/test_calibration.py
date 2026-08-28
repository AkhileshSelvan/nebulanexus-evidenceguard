"""Regression tests for the real-world forensic calibration.

Background: a bundle of nine legitimate scanned credentials scored 82.73 ->
critical -> reject. The audit showed the pixel detectors were keying on the
scan/PDF delivery pipeline rather than on manipulation -- copy_move fired on
9/9 genuine documents and scored up to 91.8, higher than the 25.9 scored by the
deliberately forged copy-move fixture.

These tests pin the fix in both directions: pipeline artifacts must not drive
risk on PDF-derived rasters, and the tampered fixtures must still be detected.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.orchestrator import run_pipeline  # noqa: E402

from modules.consistency.checker import (  # noqa: E402
    DOC_NUMBER_REUSE_CAP,
    DOC_NUMBER_REUSE_PER_DOC,
)
from modules.forensics.analyzer import (  # noqa: E402
    MATERIALITY_FLOOR,
    PDF_PIPELINE_ARTIFACT_SIGNALS,
    PDF_SCANNED_PAPER_TOLERANCE,
    apply_provenance_calibration,
)
from modules.forensics.metadata import (  # noqa: E402
    MISSING_METADATA_ABSENT_SCORE,
    MISSING_METADATA_PARTIAL_CAP,
)
from modules.risk import SOURCE_PROBABILITY_CEILING, recommend, score_bundle, score_document

CASES = _REPO_ROOT / "data" / "demo" / "cases"
PDF, JPG = "application/pdf", "image/jpeg"


def _signal(sid: str, score: float, passed: bool = False) -> dict:
    return {
        "id": sid, "label": sid, "score": score, "confidence": 0.9,
        "passed": passed, "pages": [1], "regions": [], "detail": "d",
    }


def _upload(name: str, media: str):
    return [(name, media, (CASES / name).read_bytes(), None)]


def _contribs(report: dict) -> dict[str, float]:
    out: dict[str, float] = {}
    for c in report["risk"]["contributions"]:
        out[c["signal_id"].rsplit("@", 1)[0]] = out.get(c["signal_id"].rsplit("@", 1)[0], 0.0) + c["contribution"]
    return out


# --------------------------------------------------------------------------- #
# A. legitimate scanned PDF gets no material copy_move risk contribution       #
# --------------------------------------------------------------------------- #


def test_A_copy_move_demoted_on_pdf_raster_even_at_maximum_score() -> None:
    """The exact failure observed: copy_move 91.8 on a genuine scanned page."""
    signals = [_signal("copy_move", 91.8)]
    apply_provenance_calibration(signals, is_pdf_raster=True)
    assert signals[0]["score"] == 0.0
    assert signals[0]["passed"] is True
    # the measurement survives for the reviewer
    assert "91.8" in signals[0]["detail"]
    assert "informational" in signals[0]["detail"]


def test_A_copy_move_absent_from_risk_contributions_on_pdf_bundle() -> None:
    rep = run_pipeline(_upload("clean_metadata.pdf", PDF))
    assert "copy_move" not in _contribs(rep)


def test_A_copy_move_still_evidential_on_native_image() -> None:
    """The demotion is scoped to PDF rasters; native JPEG keeps full force."""
    signals = [_signal("copy_move", 91.8)]
    apply_provenance_calibration(signals, is_pdf_raster=False)
    assert signals[0]["score"] == 91.8
    assert signals[0]["passed"] is False


# --------------------------------------------------------------------------- #
# B. PDF-induced double compression is not material risk                       #
# --------------------------------------------------------------------------- #


def test_B_double_compression_demoted_on_pdf_raster() -> None:
    signals = [_signal("double_compression", 100.0)]
    apply_provenance_calibration(signals, is_pdf_raster=True)
    assert signals[0]["score"] == 0.0
    assert signals[0]["passed"] is True


def test_B_double_compression_preserved_for_native_jpeg() -> None:
    """Requirement: do not globally disable the detector for native JPEG."""
    signals = [_signal("double_compression", 100.0)]
    apply_provenance_calibration(signals, is_pdf_raster=False)
    assert signals[0]["score"] == 100.0
    assert signals[0]["passed"] is False


def test_B_tampered_ela_jpeg_still_scores_on_double_compression() -> None:
    rep = run_pipeline(_upload("tampered_ela.jpg", JPG))
    assert "double_compression" in _contribs(rep)


# --------------------------------------------------------------------------- #
# C. repeated document number is informational / weak                          #
# --------------------------------------------------------------------------- #


def test_C_document_number_reuse_is_low_scored() -> None:
    assert DOC_NUMBER_REUSE_CAP <= 12.0
    assert DOC_NUMBER_REUSE_PER_DOC <= 4.0
    # Even a 9-document bundle sharing one registration number stays trivial.
    assert min(DOC_NUMBER_REUSE_PER_DOC * 9, DOC_NUMBER_REUSE_CAP) <= 12.0


def test_C_reused_document_number_alone_cannot_escalate() -> None:
    """A shared student/registration id must not by itself leave 'accept'."""
    cons = {
        "engine": "t", "engine_version": "1",
        "checks": [{
            "id": "document_number_reuse", "label": "reuse", "field": "document_number",
            "status": "warn",
            "score": min(DOC_NUMBER_REUSE_PER_DOC * 3, DOC_NUMBER_REUSE_CAP),
            "confidence": 0.75, "observed": [], "detail": "shared registration number",
        }],
        "cross_references": [], "score": 0.0, "summary": "",
    }
    b = score_bundle("bnd", [], cons)
    assert recommend(b)["decision"] == "accept", f"escalated at {b['score']}"


# --------------------------------------------------------------------------- #
# missing_expected_metadata is weak on scans                                   #
# --------------------------------------------------------------------------- #


def test_missing_metadata_is_weak_not_fraud_evidence() -> None:
    assert MISSING_METADATA_ABSENT_SCORE <= 15.0
    assert MISSING_METADATA_PARTIAL_CAP <= 10.0


def test_missing_metadata_across_a_whole_bundle_cannot_escalate() -> None:
    """Nine scans that all lack metadata must not add up to a decision."""
    docs = []
    for i in range(9):
        md = {
            "engine": "m", "engine_version": "1", "container": "pdf", "raw": {},
            "derived": {"created_at": None, "modified_at": None, "producer": None,
                        "creator_tool": None, "has_gps": False, "software_edits": []},
            "signals": [{"id": "missing_expected_metadata", "label": "m",
                         "score": MISSING_METADATA_ABSENT_SCORE, "confidence": 0.25,
                         "passed": False, "detail": "no metadata"}],
            "score": MISSING_METADATA_ABSENT_SCORE, "summary": "",
        }
        docs.append(score_document(f"doc_{i}", None, md, None))
    b = score_bundle("bnd", docs, None)
    assert recommend(b)["decision"] == "accept", f"escalated at {b['score']}"


# --------------------------------------------------------------------------- #
# noise_inconsistency: scanned-paper tolerance, not removal                    #
# --------------------------------------------------------------------------- #


def test_noise_inconsistency_tolerated_on_pdf_but_not_removed() -> None:
    tol = PDF_SCANNED_PAPER_TOLERANCE["noise_inconsistency"]
    below = [_signal("noise_inconsistency", tol - 10)]
    above = [_signal("noise_inconsistency", tol + 10)]
    apply_provenance_calibration(below, is_pdf_raster=True)
    apply_provenance_calibration(above, is_pdf_raster=True)
    assert below[0]["score"] == 0.0, "ordinary scan variation should not score"
    assert above[0]["score"] == tol + 10, "strong noise evidence must survive"


def test_noise_inconsistency_untouched_on_native_image() -> None:
    s = [_signal("noise_inconsistency", 37.3)]
    apply_provenance_calibration(s, is_pdf_raster=False)
    assert s[0]["score"] == 37.3


# --------------------------------------------------------------------------- #
# ELA is preserved end to end; it is immaterial by weight, not by muting       #
# --------------------------------------------------------------------------- #


def test_no_global_materiality_floor_is_applied() -> None:
    """A prototyped global floor was removed on purpose.

    Overriding a detector's own `passed` verdict from the aggregator changes the
    signal's meaning for every consumer. ELA stays intact; it simply carries
    little weight.
    """
    assert MATERIALITY_FLOOR == 0.0


@pytest.mark.parametrize("score", [0.1, 0.9, 3.4, 4.1, 60.0])
def test_ela_is_never_muted_on_native_images(score: float) -> None:
    s = [_signal("ela_hotspot", score)]
    apply_provenance_calibration(s, is_pdf_raster=False)
    assert s[0]["score"] == score
    assert s[0]["passed"] is False


def test_near_floor_ela_cannot_move_a_decision_by_weight_alone() -> None:
    """Nine documents each with a near-noise ELA reading must stay 'accept'."""
    docs = []
    for i in range(9):
        f = {"engine": "f", "engine_version": "1",
             "signals": [_signal("ela_hotspot", 3.4)], "score": 3.4, "summary": ""}
        docs.append(score_document(f"doc_{i}", f, None, None))
    b = score_bundle("bnd", docs, None)
    assert recommend(b)["decision"] == "accept", f"escalated at {b['score']}"


# --------------------------------------------------------------------------- #
# D / E / F. fixtures still behave                                             #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name,media", [
    ("genuine_clean.jpg", JPG),
    ("clean_metadata.pdf", PDF),
    ("low_quality_scan.jpg", JPG),
])
def test_D_clean_fixtures_remain_accept(name: str, media: str) -> None:
    rep = run_pipeline(_upload(name, media))
    assert rep["recommendation"]["decision"] == "accept", \
        f"{name} -> {rep['risk']['score']} {rep['recommendation']['decision']}"


@pytest.mark.parametrize("name,media", [
    ("tampered_ela.jpg", JPG),
    ("tampered_copymove.jpg", JPG),
    ("tampered_metadata.pdf", PDF),
])
def test_F_tampered_fixtures_remain_detected(name: str, media: str) -> None:
    rep = run_pipeline(_upload(name, media))
    assert rep["recommendation"]["decision"] in ("review", "reject"), \
        f"{name} -> {rep['risk']['score']} {rep['recommendation']['decision']}"
    assert rep["risk"]["score"] > 20.0, f"{name} scored only {rep['risk']['score']}"


def test_E_contradiction_still_escalates() -> None:
    """Cross-document contradiction is unaffected by forensic calibration."""
    import io
    import pymupdf

    def pdf(title: str, lines: list[str]) -> bytes:
        d = pymupdf.open()
        p = d.new_page(width=595, height=842)
        p.insert_text((60, 90), title, fontsize=18, fontname="helv")
        y = 150
        for ln in lines:
            p.insert_text((60, y), ln, fontsize=13, fontname="helv")
            y += 32
        d.set_metadata({"producer": "EG test", "creator": "EG test",
                        "creationDate": "D:20260810090000+00'00'",
                        "modDate": "D:20260810090000+00'00'"})
        out = d.tobytes()
        d.close()
        return out

    a = pdf("IDENTITY CARD", ["Full Name: Jane Amara Doe", "Date of Birth: 14/03/1990"])
    b = pdf("PAYSLIP", ["Employee Name: Robert Keith Mensah", "Date of Birth: 02/11/1978"])
    rep = run_pipeline([("id.pdf", PDF, a, None), ("pay.pdf", PDF, b, None)])
    fails = [c["id"] for c in rep["consistency"]["checks"] if c["status"] in ("warn", "fail")]
    assert "name_match" in fails and "dob_match" in fails
    assert rep["recommendation"]["decision"] in ("review", "reject")


# --------------------------------------------------------------------------- #
# G. single-source safety guarantee preserved                                  #
# --------------------------------------------------------------------------- #


def test_G_no_single_source_can_reject() -> None:
    for source, ceiling in SOURCE_PROBABILITY_CEILING.items():
        assert ceiling * 100.0 < 75.0, f"{source} could reject alone"


def test_G_saturated_forensics_alone_still_only_reviews() -> None:
    f = {
        "engine": "f", "engine_version": "1",
        "signals": [_signal(f"sig_{i}", 100.0) for i in range(30)],
        "score": 100.0, "summary": "",
    }
    doc = score_document("doc_1", f, None, None)
    b = score_bundle("bnd", [doc], None)
    assert recommend(b)["decision"] != "reject"


# --------------------------------------------------------------------------- #
# H. determinism                                                               #
# --------------------------------------------------------------------------- #


def test_H_repeated_runs_are_identical() -> None:
    def fingerprint() -> tuple:
        rep = run_pipeline(_upload("tampered_ela.jpg", JPG))
        return (
            rep["risk"]["score"], rep["risk"]["severity"],
            rep["recommendation"]["decision"],
            tuple(sorted((c["source"], c["signal_id"].rsplit("@", 1)[0], c["contribution"])
                         for c in rep["risk"]["contributions"])),
        )

    first = fingerprint()
    for _ in range(2):
        assert fingerprint() == first


def test_H_calibration_is_idempotent() -> None:
    """Applying calibration twice must not change the outcome."""
    s = [_signal("copy_move", 91.8), _signal("ela_hotspot", 60.0)]
    apply_provenance_calibration(s, is_pdf_raster=True)
    once = [(x["id"], x["score"], x["passed"]) for x in s]
    apply_provenance_calibration(s, is_pdf_raster=True)
    assert [(x["id"], x["score"], x["passed"]) for x in s] == once


def test_pipeline_artifact_set_is_scoped_and_documented() -> None:
    """Guard against the demotion list quietly growing to cover real evidence."""
    assert PDF_PIPELINE_ARTIFACT_SIGNALS == frozenset({"copy_move", "double_compression"})
