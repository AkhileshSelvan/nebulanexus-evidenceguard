"""Health / liveness endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.config import SERVICE_NAME, VERSION
from app.timeutil import now_iso

router = APIRouter(tags=["meta"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Returns 200 as long as the process is up."""
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "version": VERSION,
        "time": now_iso(),
    }
