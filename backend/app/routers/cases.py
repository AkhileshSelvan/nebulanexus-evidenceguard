"""Case storage, reviewer decisions, and audit trail.

Every `POST /api/v1/verify` persists its report as a "case" (see
`app.routers.verify`). This router lets a reviewer list cases, pull one up,
record a decision on it, and read its audit trail. See
`docs/API_CONTRACT.md` §12 for the JSON shapes.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app import audit, storage
from app.timeutil import now_iso

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


class DecisionRequest(BaseModel):
    decision: Literal["accept", "review", "reject"]
    reviewer_name: str = Field(min_length=1, max_length=200)
    notes: str | None = Field(default=None, max_length=4000)


@router.get("")
def list_cases(limit: int = 50, offset: int = 0) -> dict:
    """Newest-first case summaries. Use `GET /cases/{report_id}` for the full report."""
    if not (1 <= limit <= 200):
        raise HTTPException(status_code=422, detail="limit must be between 1 and 200.")
    if offset < 0:
        raise HTTPException(status_code=422, detail="offset must be >= 0.")
    return {"cases": storage.list_cases(limit=limit, offset=offset)}


@router.get("/{report_id}")
def get_case(report_id: str) -> dict:
    """The full persisted `VerificationReport` plus the current reviewer decision."""
    try:
        return storage.get_case(report_id)
    except storage.CaseNotFoundError:
        raise HTTPException(status_code=404, detail=f"No case with report_id '{report_id}'.")


@router.post("/{report_id}/decision")
def record_decision(report_id: str, body: DecisionRequest) -> dict:
    """Record (or overwrite) a reviewer's decision on a case. Always audited."""
    if not storage.case_exists(report_id):
        raise HTTPException(status_code=404, detail=f"No case with report_id '{report_id}'.")

    reviewed_at = now_iso()
    storage.record_decision(
        report_id,
        decision=body.decision,
        reviewer_name=body.reviewer_name,
        notes=body.notes,
        reviewed_at=reviewed_at,
    )
    audit.record(
        report_id=report_id,
        event_type="decision_recorded",
        actor=body.reviewer_name,
        detail={"decision": body.decision, "notes": body.notes},
    )
    return {
        "report_id": report_id,
        "reviewer_decision": body.decision,
        "reviewer_name": body.reviewer_name,
        "reviewer_notes": body.notes,
        "reviewed_at": reviewed_at,
    }


@router.get("/{report_id}/audit")
def get_audit_trail(report_id: str) -> dict:
    """Full audit trail for one case, oldest first."""
    if not storage.case_exists(report_id):
        raise HTTPException(status_code=404, detail=f"No case with report_id '{report_id}'.")
    return {"report_id": report_id, "events": audit.list_for_case(report_id)}
