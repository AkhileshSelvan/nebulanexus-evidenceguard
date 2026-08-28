"""Shared UTC timestamp helper.

`docs/API_CONTRACT.md` requires every timestamp to be an ISO 8601 UTC string
with a literal ``Z`` suffix, e.g. ``2026-08-28T10:36:00Z`` — no microseconds,
no ``+00:00``. `datetime.isoformat()` alone produces neither of those, so
every place in the backend that stamps a time goes through :func:`now_iso`
instead of calling `datetime.now(timezone.utc).isoformat()` directly.
"""

from __future__ import annotations

from datetime import datetime, timezone


def now_iso() -> str:
    """Current UTC time as a contract-shaped string, e.g. ``2026-08-28T10:36:00Z``."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
