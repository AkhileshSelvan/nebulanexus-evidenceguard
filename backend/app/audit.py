"""Append-only audit trail.

Every mutating action on a case (created, reviewer decision recorded) goes
through :func:`record`. Rows are never updated or deleted — callers that want
"what changed" just read the ordered log for a ``report_id``.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Literal

from app.db import get_connection
from app.timeutil import now_iso

AuditEventType = Literal["report_created", "decision_recorded"]


def record(
    *,
    report_id: str,
    event_type: AuditEventType,
    actor: str | None = None,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append one audit event and return it as a plain dict."""
    event = {
        "id": f"aud_{uuid.uuid4().hex[:12]}",
        "report_id": report_id,
        "event_type": event_type,
        "actor": actor,
        "detail": detail or {},
        "at": now_iso(),
    }
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO audit_log (id, report_id, event_type, actor, detail, at)
        VALUES (:id, :report_id, :event_type, :actor, :detail, :at)
        """,
        {**event, "detail": json.dumps(event["detail"])},
    )
    conn.commit()
    return event


def list_for_case(report_id: str) -> list[dict[str, Any]]:
    """Full audit trail for one case, oldest first.

    Ordered by ``rowid`` (SQLite's implicit, monotonically-increasing insert
    order) rather than ``at``: timestamps are second-precision (see
    `app.timeutil.now_iso`), so two events recorded in the same second are
    common and would otherwise tie. ``rowid`` always reflects true insertion
    order, which for an append-only log *is* chronological order.
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, report_id, event_type, actor, detail, at "
        "FROM audit_log WHERE report_id = ? ORDER BY rowid ASC",
        (report_id,),
    ).fetchall()
    out = []
    for row in rows:
        entry = dict(row)
        entry["detail"] = json.loads(entry["detail"]) if entry["detail"] else {}
        out.append(entry)
    return out
