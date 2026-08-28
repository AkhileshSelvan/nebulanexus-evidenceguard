"""FastAPI application entry point.

Run locally:
    uvicorn app.main:app --reload --port 8000

The app is intentionally thin: it ingests files, calls the analysis modules
(see ``app.orchestrator``), assembles the ``VerificationReport`` from the shared
contract, and serves it. No detection logic lives here.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS, SERVICE_NAME, VERSION
from app.routers import health, verify

app = FastAPI(
    title="EvidenceGuard API",
    version=VERSION,
    summary="AI-assisted document verification & fraud detection — verify the evidence, not just the document.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(verify.router)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    """Tiny landing payload so hitting the bare host isn't a 404."""
    return {
        "service": SERVICE_NAME,
        "version": VERSION,
        "docs": "/docs",
        "health": "/health",
    }
