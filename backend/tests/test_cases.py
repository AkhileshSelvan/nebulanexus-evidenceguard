"""Case storage, reviewer decisions, and the audit trail."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _create_case() -> str:
    """POST /verify once and return the new report_id."""
    files = [
        ("files", ("id_card.png", io.BytesIO(b"fake-image-bytes"), "image/png")),
    ]
    resp = client.post("/api/v1/verify", files=files)
    assert resp.status_code == 200, resp.text
    return resp.json()["report_id"]


def test_verify_persists_a_case() -> None:
    report_id = _create_case()

    resp = client.get("/api/v1/cases")
    assert resp.status_code == 200
    summaries = resp.json()["cases"]
    assert any(c["report_id"] == report_id for c in summaries)

    mine = next(c for c in summaries if c["report_id"] == report_id)
    assert mine["document_count"] == 1
    assert mine["reviewer_decision"] is None  # nobody has reviewed it yet


def test_get_case_returns_full_report() -> None:
    report_id = _create_case()

    resp = client.get(f"/api/v1/cases/{report_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["report"]["report_id"] == report_id
    assert body["reviewer_decision"] is None
    # the full contract-shaped report should be intact, not just a summary
    assert "documents" in body["report"]
    assert "recommendation" in body["report"]


def test_get_unknown_case_is_404() -> None:
    resp = client.get("/api/v1/cases/rep_doesnotexist")
    assert resp.status_code == 404


def test_recording_a_decision_updates_the_case_and_is_audited() -> None:
    report_id = _create_case()

    resp = client.post(
        f"/api/v1/cases/{report_id}/decision",
        json={"decision": "review", "reviewer_name": "Bagavathianu", "notes": "Needs a second pass."},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["reviewer_decision"] == "review"
    assert body["reviewer_name"] == "Bagavathianu"

    # the case reflects the decision
    case = client.get(f"/api/v1/cases/{report_id}").json()
    assert case["reviewer_decision"] == "review"
    assert case["reviewer_notes"] == "Needs a second pass."
    assert case["reviewed_at"] is not None

    # ...and it's in the audit trail, alongside the creation event
    audit_resp = client.get(f"/api/v1/cases/{report_id}/audit")
    assert audit_resp.status_code == 200
    events = audit_resp.json()["events"]
    event_types = [e["event_type"] for e in events]
    assert event_types == ["report_created", "decision_recorded"]
    assert events[-1]["actor"] == "Bagavathianu"
    assert events[-1]["detail"]["decision"] == "review"


def test_decision_can_be_overwritten_and_both_are_audited() -> None:
    report_id = _create_case()

    client.post(
        f"/api/v1/cases/{report_id}/decision",
        json={"decision": "review", "reviewer_name": "Agalya"},
    )
    resp = client.post(
        f"/api/v1/cases/{report_id}/decision",
        json={"decision": "accept", "reviewer_name": "Akhilesh", "notes": "Looks clean on recheck."},
    )
    assert resp.status_code == 200
    assert resp.json()["reviewer_decision"] == "accept"

    case = client.get(f"/api/v1/cases/{report_id}").json()
    assert case["reviewer_decision"] == "accept"  # latest wins
    assert case["reviewer_name"] == "Akhilesh"

    events = client.get(f"/api/v1/cases/{report_id}/audit").json()["events"]
    decisions = [e for e in events if e["event_type"] == "decision_recorded"]
    assert len(decisions) == 2  # nothing overwritten, history preserved
    assert [d["actor"] for d in decisions] == ["Agalya", "Akhilesh"]


def test_decision_on_unknown_case_is_404() -> None:
    resp = client.post(
        "/api/v1/cases/rep_doesnotexist/decision",
        json={"decision": "accept", "reviewer_name": "Someone"},
    )
    assert resp.status_code == 404


def test_decision_requires_a_valid_choice() -> None:
    report_id = _create_case()
    resp = client.post(
        f"/api/v1/cases/{report_id}/decision",
        json={"decision": "maybe", "reviewer_name": "Someone"},
    )
    assert resp.status_code == 422


def test_audit_trail_on_unknown_case_is_404() -> None:
    resp = client.get("/api/v1/cases/rep_doesnotexist/audit")
    assert resp.status_code == 404
