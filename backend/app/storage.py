"""Case persistence.

A "case" is one persisted ``VerificationReport`` (contract §0) plus whatever
a human reviewer later decides about it. This module is the only place that
writes to the ``cases`` table; :mod:`app.audit` owns ``audit_log``.

Kept deliberately dumb: the full report is stored as JSON (it's already
contract-valid by the time it gets here — nothing here re-derives or
re-validates analysis results), with a few columns pulled out for cheap
listing/filtering.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from app.db import get_connection

ReviewDecision = Literal["accept", "review", "reject"]


class CaseNotFoundError(LookupError):
    """Raised when a report_id has no matching row in ``cases``."""


def save_case(report: dict[str, Any]) -> None:
    """Persist a freshly produced ``VerificationReport`` as a new case."""
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO cases (
            report_id, bundle_id, created_at, status, document_count,
            risk_score, risk_severity, recommendation_decision, report_json
        ) VALUES (
            :report_id, :bundle_id, :created_at, :status, :document_count,
            :risk_score, :risk_severity, :recommendation_decision, :report_json
        )
        """,
        {
            "report_id": report["report_id"],
            "bundle_id": report["bundle"]["bundle_id"],
            "created_at": report["created_at"],
            "status": report["status"],
            "document_count": report["bundle"]["document_count"],
            "risk_score": report.get("risk", {}).get("score"),
            "risk_severity": report.get("risk", {}).get("severity"),
            "recommendation_decision": report.get("recommendation", {}).get("decision"),
            "report_json": json.dumps(report),
        },
    )
    conn.commit()


def _row_to_summary(row) -> dict[str, Any]:
    return {
        "report_id": row["report_id"],
        "bundle_id": row["bundle_id"],
        "created_at": row["created_at"],
        "status": row["status"],
        "document_count": row["document_count"],
        "risk_score": row["risk_score"],
        "risk_severity": row["risk_severity"],
        "recommendation_decision": row["recommendation_decision"],
        "reviewer_decision": row["reviewer_decision"],
        "reviewer_name": row["reviewer_name"],
        "reviewer_notes": row["reviewer_notes"],
        "reviewed_at": row["reviewed_at"],
    }


def list_cases(limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    """Newest-first case summaries (no full report body — use :func:`get_case`).

    Ordered by ``rowid`` (insertion order) rather than ``created_at`` alone:
    timestamps are second-precision (see `app.timeutil.now_iso`), so two
    cases created in the same second would otherwise tie in an unspecified
    order. ``rowid`` DESC always agrees with "newest first" for an
    insert-only table.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT report_id, bundle_id, created_at, status, document_count,
               risk_score, risk_severity, recommendation_decision,
               reviewer_decision, reviewer_name, reviewer_notes, reviewed_at
        FROM cases ORDER BY rowid DESC LIMIT ? OFFSET ?
        """,
        (limit, offset),
    ).fetchall()
    return [_row_to_summary(r) for r in rows]


def get_case(report_id: str) -> dict[str, Any]:
    """Full stored ``VerificationReport`` plus the current reviewer decision."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM cases WHERE report_id = ?", (report_id,)
    ).fetchone()
    if row is None:
        raise CaseNotFoundError(report_id)
    report = json.loads(row["report_json"])
    return {
        "report": report,
        "reviewer_decision": row["reviewer_decision"],
        "reviewer_name": row["reviewer_name"],
        "reviewer_notes": row["reviewer_notes"],
        "reviewed_at": row["reviewed_at"],
    }


def case_exists(report_id: str) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM cases WHERE report_id = ?", (report_id,)
    ).fetchone()
    return row is not None


def record_decision(
    report_id: str,
    *,
    decision: ReviewDecision,
    reviewer_name: str,
    notes: str | None,
    reviewed_at: str,
) -> None:
    """Overwrite the case's current reviewer decision.

    A case holds one *current* decision (the reviewer's latest call); the
    full history of who decided what and when lives in ``audit_log``, which
    :mod:`app.routers.cases` writes to alongside this call.
    """
    conn = get_connection()
    if not case_exists(report_id):
        raise CaseNotFoundError(report_id)
    conn.execute(
        """
        UPDATE cases
        SET reviewer_decision = ?, reviewer_name = ?, reviewer_notes = ?, reviewed_at = ?
        WHERE report_id = ?
        """,
        (decision, reviewer_name, notes, reviewed_at, report_id),
    )
    conn.commit()
