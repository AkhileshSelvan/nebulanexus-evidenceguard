"""Tests for the forensics and metadata modules."""

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


def test_genuine_clean_passes():
    """Test that a clean document passes all forensics checks."""
    fixture = FIXTURE_DIR / "genuine_clean.jpg"
    if not fixture.exists():
        pytest.skip(f"Fixture {fixture} not generated")
        
    with open(fixture, "rb") as f:
        data = f.read()
        
    doc = build_document(
        bundle_id="test",
        filename="genuine_clean.jpg",
        media_type="image/jpeg",
        data=data,
        declared_type="id_card",
    )
    
    forensics = analyze(doc, image_paths=[], file_data=data)
    
    assert forensics["engine"] == "evidenceguard-forensics"
    assert forensics["score"] < 50.0, (
        f"Clean image scored {forensics['score']}/100 — expected low concern"
    )
    
    # No signals should flag as failed
    failed = [s for s in forensics["signals"] if not s["passed"]]
    assert len(failed) == 0, (
        f"Clean image triggered {len(failed)} signal(s): "
        + ", ".join(f"{s['id']}={s['score']}" for s in failed)
    )
        

def test_tampered_ela_detected():
    """Test that ELA detects the spliced patch."""
    fixture = FIXTURE_DIR / "tampered_ela.jpg"
    if not fixture.exists():
        pytest.skip(f"Fixture {fixture} not generated")
        
    with open(fixture, "rb") as f:
        data = f.read()
        
    doc = build_document(
        bundle_id="test",
        filename="tampered_ela.jpg",
        media_type="image/jpeg",
        data=data,
        declared_type="id_card",
    )
    
    forensics = analyze(doc, image_paths=[], file_data=data)
    
    # ELA signal should fire
    ela_signals = [s for s in forensics["signals"] if s["id"] == "ela_hotspot"]
    assert len(ela_signals) == 1
    assert ela_signals[0]["passed"] is False, (
        f"ELA should detect splice; detail: {ela_signals[0]['detail']}"
    )
    assert ela_signals[0]["score"] > 0.0, (
        f"ELA score should be non-zero; got {ela_signals[0]['score']}"
    )
    
    # Regions should be detected in the patch area
    assert len(ela_signals[0]["regions"]) > 0
    
    
def test_low_quality_noise():
    """Test that noise inconsistency detects spliced patches on noisy scans."""
    fixture = FIXTURE_DIR / "low_quality_scan.jpg"
    if not fixture.exists():
        pytest.skip(f"Fixture {fixture} not generated")
        
    with open(fixture, "rb") as f:
        data = f.read()
        
    doc = build_document(
        bundle_id="test",
        filename="low_quality_scan.jpg",
        media_type="image/jpeg",
        data=data,
        declared_type="id_card",
    )
    
    forensics = analyze(doc, image_paths=[], file_data=data)
    
    # Noise inconsistency should fire
    noise_signals = [s for s in forensics["signals"] if s["id"] == "noise_inconsistency"]
    assert len(noise_signals) == 1
    assert noise_signals[0]["passed"] is False


def test_metadata_future_timestamp_and_editor():
    """Test that metadata plausibility checks catch obvious tampering."""
    fixture = FIXTURE_DIR / "tampered_metadata.pdf"
    if not fixture.exists():
        pytest.skip(f"Fixture {fixture} not generated")
        
    with open(fixture, "rb") as f:
        data = f.read()
        
    doc = build_document(
        bundle_id="test",
        filename="tampered_metadata.pdf",
        media_type="application/pdf",
        data=data,
        declared_type="bank_statement",
    )
    
    metadata = extract_metadata(doc, file_path=None, file_data=data)
    
    assert metadata["engine"] == "evidenceguard-metadata"
    
    # Future timestamp signal should fail
    future_sigs = [s for s in metadata["signals"] if s["id"] == "future_timestamp"]
    assert len(future_sigs) == 1
    assert future_sigs[0]["passed"] is False
    
    # Image editor signal should fail
    editor_sigs = [s for s in metadata["signals"] if s["id"] == "editor_is_image_tool"]
    assert len(editor_sigs) == 1
    assert editor_sigs[0]["passed"] is False
    
    # Producer mismatch should fail (bank statement from Photoshop)
    mismatch_sigs = [s for s in metadata["signals"] if s["id"] == "producer_mismatch_for_issuer"]
    assert len(mismatch_sigs) == 1
    assert mismatch_sigs[0]["passed"] is False


def test_pipeline_integration():
    """Test the full pipeline with the mocked orchestrator."""
    fixture = FIXTURE_DIR / "genuine_clean.jpg"
    if not fixture.exists():
        pytest.skip(f"Fixture {fixture} not generated")
        
    with open(fixture, "rb") as f:
        data = f.read()
        
    files = [
        ("files", ("genuine_clean.jpg", data, "image/jpeg")),
    ]
    resp = client.post("/api/v1/verify", files=files)
    assert resp.status_code == 200
    report = resp.json()
    
    # Verify the report contains real forensics sections
    doc_entry = report["documents"][0]
    
    assert doc_entry["forensics"]["engine"] == "evidenceguard-forensics"
    assert len(doc_entry["forensics"]["signals"]) > 0
    
    assert doc_entry["metadata"]["engine"] == "evidenceguard-metadata"
    assert len(doc_entry["metadata"]["signals"]) > 0
