"""Foundation smoke tests: the app boots, /health answers, the pipeline runs."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "evidenceguard-backend"
    assert "time" in body


def test_ping() -> None:
    resp = client.get("/api/v1/ping")
    assert resp.status_code == 200
    assert resp.json() == {"message": "pong"}


def test_verify_returns_contract_shaped_report() -> None:
    files = [
        ("files", ("id_card.png", io.BytesIO(b"fake-image-bytes"), "image/png")),
        ("files", ("payslip.pdf", io.BytesIO(b"%PDF-1.7 fake"), "application/pdf")),
    ]
    resp = client.post("/api/v1/verify", files=files)
    assert resp.status_code == 200, resp.text
    report = resp.json()

    # top-level shape (contract §0)
    for key in (
        "report_id",
        "created_at",
        "status",
        "bundle",
        "documents",
        "consistency",
        "risk",
        "recommendation",
        "explanation",
        "errors",
    ):
        assert key in report, f"missing '{key}'"

    assert report["bundle"]["document_count"] == 2
    assert len(report["documents"]) == 2

    entry = report["documents"][0]
    for key in ("document", "extraction", "forensics", "metadata", "risk"):
        assert key in entry

    # ingest is real: hash + size populated
    assert len(entry["document"]["sha256"]) == 64
    assert entry["document"]["byte_size"] > 0

    # risk section (contract §6)
    assert report["risk"]["scope"] == "bundle"
    assert report["risk"]["severity"] in {"low", "medium", "high", "critical"}
    assert report["recommendation"]["decision"] in {"accept", "review", "reject"}
