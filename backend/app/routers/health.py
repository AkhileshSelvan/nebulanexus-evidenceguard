"""Health / liveness endpoint."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import SERVICE_NAME, VERSION

router = APIRouter(tags=["meta"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Returns 200 as long as the process is up."""
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "version": VERSION,
        "time": datetime.now(timezone.utc).isoformat(),
    }
