"""SQLite case store.

Two tables:

``cases``
    One row per verification report. Stores the full ``VerificationReport``
    JSON plus a handful of denormalized columns (risk score, severity,
    recommendation) so the case list doesn't need to parse every row's JSON,
    and the latest reviewer decision.

``audit_log``
    Append-only. One row per notable event on a case: created, decision
    recorded, decision changed. Nothing is ever updated or deleted here —
    that is the point of an audit trail.

A single module-level connection is reused for the life of the process
(``check_same_thread=False`` because FastAPI's TestClient and uvicorn's
threadpool can call in from different threads). For ``DB_PATH == ":memory:"``
this also happens to be what makes the in-memory DB usable across requests
at all — a fresh ``:memory:`` connection per call would see an empty DB
every time.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.config import DB_PATH

_connection: sqlite3.Connection | None = None


_SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    report_id                TEXT PRIMARY KEY,
    bundle_id                TEXT NOT NULL,
    created_at                TEXT NOT NULL,
    status                    TEXT NOT NULL,
    document_count            INTEGER NOT NULL,
    risk_score                REAL,
    risk_severity              TEXT,
    recommendation_decision    TEXT,
    report_json                 TEXT NOT NULL,
    reviewer_decision          TEXT,
    reviewer_name               TEXT,
    reviewer_notes                TEXT,
    reviewed_at                     TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id                TEXT PRIMARY KEY,
    report_id          TEXT NOT NULL,
    event_type          TEXT NOT NULL,
    actor                 TEXT,
    detail                  TEXT,
    at                        TEXT NOT NULL,
    FOREIGN KEY (report_id) REFERENCES cases (report_id)
);

CREATE INDEX IF NOT EXISTS idx_audit_log_report_id ON audit_log (report_id);
CREATE INDEX IF NOT EXISTS idx_cases_created_at ON cases (created_at);
"""


def get_connection() -> sqlite3.Connection:
    """Return the shared connection, creating and migrating it on first use."""
    global _connection
    if _connection is None:
        if DB_PATH != ":memory:":
            Path(DB_PATH).resolve().parent.mkdir(parents=True, exist_ok=True)
        _connection = sqlite3.connect(DB_PATH, check_same_thread=False)
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA foreign_keys = ON")
        _connection.executescript(_SCHEMA)
        _connection.commit()
    return _connection


def reset_connection() -> None:
    """Close and drop the cached connection. Test-only escape hatch so a test
    that wants a truly fresh ``:memory:`` DB can force a reconnect."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None
