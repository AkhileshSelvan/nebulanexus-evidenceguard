"""Comprehensive tests for forensics and metadata modules.

Covers Issue #6 (forensic evidence) and Issue #8 (synthetic demo cases).

Test categories:
  - Genuine/clean: all signals pass
  - Tampered ELA: error-level analysis detects spliced patch
  - Tampered copy-move: duplicated region detected
  - Low-quality scan: noise inconsistency detected
  - Metadata (tampered): future timestamps, image editor, producer mismatch
  - Metadata (contradictory): modified-before-created, timezone mismatch
  - Metadata (clean): all metadata signals pass
  - Pipeline integration: full orchestrator round-trip
"""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.orchestrator import build_document
from modules.forensics import analyze, extract_metadata

# Use the data/demo/cases directory for test fixtures
FIXTURE_DIR = Path(__file__).resolve().parents[2] / "data" / "demo" / "cases"

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_fixture(name: str) -> bytes:
    """Load a fixture file, skipping if not generated."""
    path = FIXTURE_DIR / name
    if not path.exists():
        pytest.skip(f"Fixture {path} not generated — run scripts/generate_fixtures.py")
    return path.read_bytes()


def _make_doc(name: str, media_type: str, data: bytes, declared_type: str = "id_card"):
    return build_document(
        bundle_id="test",
        filename=name,
        media_type=media_type,
        data=data,
        declared_type=declared_type,
    )


def _signal(signals: list, signal_id: str):
    """Find a signal by ID; assert it exists."""
    matches = [s for s in signals if s["id"] == signal_id]
    assert len(matches) == 1, f"Expected exactly 1 signal '{signal_id}', got {len(matches)}"
    return matches[0]


# ---------------------------------------------------------------------------
# §1  Genuine / clean image
# ---------------------------------------------------------------------------


class TestGenuineClean:
    """A clean image should not trigger any forensic signals."""

    @pytest.fixture
    def forensics(self):
        data = _load_fixture("genuine_clean.jpg")
        doc = _make_doc("genuine_clean.jpg", "image/jpeg", data)
        return analyze(doc, image_paths=[], file_data=data)

    def test_engine_version(self, forensics):
        assert forensics["engine"] == "evidenceguard-forensics"
        assert forensics["engine_version"]

    def test_score_is_low(self, forensics):
        assert forensics["score"] < 50.0, (
            f"Clean image scored {forensics['score']}/100"
        )

    def test_all_signals_pass(self, forensics):
        failed = [s for s in forensics["signals"] if not s["passed"]]
        assert len(failed) == 0, (
            "Clean image triggered: "
            + ", ".join(f"{s['id']}(score={s['score']})" for s in failed)
        )

    def test_signals_have_required_fields(self, forensics):
        for sig in forensics["signals"]:
            assert "id" in sig
            assert "label" in sig
            assert "score" in sig
            assert "confidence" in sig
            assert "passed" in sig
            assert "pages" in sig
            assert "regions" in sig
            assert "detail" in sig


# ---------------------------------------------------------------------------
# §2  Tampered — ELA detection
# ---------------------------------------------------------------------------


class TestTamperedELA:
    """An image with a spliced high-frequency patch should trigger ELA."""

    @pytest.fixture
    def forensics(self):
        data = _load_fixture("tampered_ela.jpg")
        doc = _make_doc("tampered_ela.jpg", "image/jpeg", data)
        return analyze(doc, image_paths=[], file_data=data)

    def test_ela_fires(self, forensics):
        sig = _signal(forensics["signals"], "ela_hotspot")
        assert sig["passed"] is False, f"ELA should fire; detail: {sig['detail']}"

    def test_ela_has_regions(self, forensics):
        sig = _signal(forensics["signals"], "ela_hotspot")
        assert len(sig["regions"]) > 0, "ELA should report anomalous regions"

    def test_ela_score_nonzero(self, forensics):
        sig = _signal(forensics["signals"], "ela_hotspot")
        assert sig["score"] > 0.0

    def test_double_compression_fires(self, forensics):
        """The tampered image was double-compressed (Q=50 then Q=95)."""
        sig = _signal(forensics["signals"], "double_compression")
        assert sig["passed"] is False


# ---------------------------------------------------------------------------
# §3  Tampered — copy-move detection
# ---------------------------------------------------------------------------


class TestTamperedCopyMove:
    """An image with a duplicated region should trigger copy-move."""

    @pytest.fixture
    def forensics(self):
        data = _load_fixture("tampered_copymove.jpg")
        doc = _make_doc("tampered_copymove.jpg", "image/jpeg", data)
        return analyze(doc, image_paths=[], file_data=data)

    def test_copy_move_fires(self, forensics):
        sig = _signal(forensics["signals"], "copy_move")
        assert sig["passed"] is False, f"Copy-move should fire; detail: {sig['detail']}"

    def test_copy_move_has_regions(self, forensics):
        sig = _signal(forensics["signals"], "copy_move")
        assert len(sig["regions"]) > 0, "Copy-move should report matched regions"


# ---------------------------------------------------------------------------
# §4  Low-quality scan — noise inconsistency
# ---------------------------------------------------------------------------


class TestLowQualityScan:
    """A noisy scan with a smooth splice should trigger noise inconsistency."""

    @pytest.fixture
    def forensics(self):
        data = _load_fixture("low_quality_scan.jpg")
        doc = _make_doc("low_quality_scan.jpg", "image/jpeg", data)
        return analyze(doc, image_paths=[], file_data=data)

    def test_noise_inconsistency_fires(self, forensics):
        sig = _signal(forensics["signals"], "noise_inconsistency")
        assert sig["passed"] is False

    def test_noise_has_regions(self, forensics):
        sig = _signal(forensics["signals"], "noise_inconsistency")
        assert len(sig["regions"]) > 0


# ---------------------------------------------------------------------------
# §5  Metadata — tampered PDF
# ---------------------------------------------------------------------------


class TestTamperedMetadata:
    """A PDF with Photoshop producer and future dates."""

    @pytest.fixture
    def metadata(self):
        data = _load_fixture("tampered_metadata.pdf")
        doc = _make_doc("tampered_metadata.pdf", "application/pdf", data, "bank_statement")
        return extract_metadata(doc, file_path=None, file_data=data)

    def test_engine(self, metadata):
        assert metadata["engine"] == "evidenceguard-metadata"

    def test_future_timestamp(self, metadata):
        sig = _signal(metadata["signals"], "future_timestamp")
        assert sig["passed"] is False

    def test_editor_is_image_tool(self, metadata):
        sig = _signal(metadata["signals"], "editor_is_image_tool")
        assert sig["passed"] is False

    def test_producer_mismatch(self, metadata):
        sig = _signal(metadata["signals"], "producer_mismatch_for_issuer")
        assert sig["passed"] is False

    def test_derived_fields(self, metadata):
        """The derived fields should reflect the injected metadata."""
        d = metadata["derived"]
        assert d["producer"] is not None
        assert "photoshop" in d["producer"].lower()
        assert len(d["software_edits"]) > 0


# ---------------------------------------------------------------------------
# §6  Metadata — contradictory dates
# ---------------------------------------------------------------------------


class TestContradictoryMetadata:
    """A PDF where modified date is before creation date."""

    @pytest.fixture
    def metadata(self):
        data = _load_fixture("contradictory_metadata.pdf")
        doc = _make_doc("contradictory_metadata.pdf", "application/pdf", data, "payslip")
        return extract_metadata(doc, file_path=None, file_data=data)

    def test_modified_before_creation(self, metadata):
        sig = _signal(metadata["signals"], "modified_after_creation")
        assert sig["passed"] is False, f"Should detect modified-before-created; {sig['detail']}"
        assert sig["score"] >= 50.0, "Modified-before-created should have high score"


# ---------------------------------------------------------------------------
# §7  Metadata — clean PDF
# ---------------------------------------------------------------------------


class TestCleanMetadata:
    """A PDF with consistent, plausible metadata."""

    @pytest.fixture
    def metadata(self):
        data = _load_fixture("clean_metadata.pdf")
        doc = _make_doc("clean_metadata.pdf", "application/pdf", data, "payslip")
        return extract_metadata(doc, file_path=None, file_data=data)

    def test_all_signals_pass(self, metadata):
        failed = [s for s in metadata["signals"] if not s["passed"]]
        assert len(failed) == 0, (
            "Clean PDF triggered: "
            + ", ".join(f"{s['id']}(score={s['score']})" for s in failed)
        )

    def test_metadata_was_extracted(self, metadata):
        """Should have extracted raw metadata from the PDF."""
        assert len(metadata["raw"]) > 0

    def test_derived_has_dates(self, metadata):
        d = metadata["derived"]
        assert d["created_at"] is not None
        assert d["modified_at"] is not None


# ---------------------------------------------------------------------------
# §8  Pipeline integration
# ---------------------------------------------------------------------------


class TestPipelineIntegration:
    """Full /api/v1/verify round-trip produces a valid report."""

    def test_single_jpeg(self):
        data = _load_fixture("genuine_clean.jpg")
        files = [("files", ("genuine_clean.jpg", data, "image/jpeg"))]
        resp = client.post("/api/v1/verify", files=files)
        assert resp.status_code == 200
        report = resp.json()

        doc_entry = report["documents"][0]
        assert doc_entry["forensics"]["engine"] == "evidenceguard-forensics"
        assert len(doc_entry["forensics"]["signals"]) > 0
        assert doc_entry["metadata"]["engine"] == "evidenceguard-metadata"
        assert len(doc_entry["metadata"]["signals"]) > 0

    def test_report_structure(self):
        data = _load_fixture("genuine_clean.jpg")
        files = [("files", ("genuine_clean.jpg", data, "image/jpeg"))]
        resp = client.post("/api/v1/verify", files=files)
        report = resp.json()

        # Top-level keys per contract §0
        assert "report_id" in report
        assert "created_at" in report
        assert "status" in report
        assert report["status"] == "complete"
        assert "bundle" in report
        assert "documents" in report
        assert "consistency" in report
        assert "risk" in report
        assert "recommendation" in report
        assert "explanation" in report
        assert "errors" in report

    def test_multi_file_bundle(self):
        """Upload two files and verify the bundle is processed."""
        jpg_data = _load_fixture("genuine_clean.jpg")
        pdf_data = _load_fixture("clean_metadata.pdf")
        files = [
            ("files", ("id_card.jpg", jpg_data, "image/jpeg")),
            ("files", ("payslip.pdf", pdf_data, "application/pdf")),
        ]
        resp = client.post("/api/v1/verify", files=files)
        assert resp.status_code == 200
        report = resp.json()
        assert report["bundle"]["document_count"] == 2
        assert len(report["documents"]) == 2
