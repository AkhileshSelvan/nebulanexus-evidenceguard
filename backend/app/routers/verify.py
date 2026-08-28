"""Verification endpoints.

`GET  /api/v1/ping`   — trivial connectivity check for the frontend.
`POST /api/v1/verify` — ingest 1..n files, return a VerificationReport, and
                        persist it as a case (see `app.storage`, `app.audit`).

FOUNDATION STATUS: `/verify` ingests real files but every analysis module is a
stub, so the report is contract-valid with placeholder findings. Case storage
and the audit trail are real.
"""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app import audit, storage
from app.config import MAX_FILE_BYTES, MAX_FILES_PER_BUNDLE
from app.orchestrator import run_pipeline

router = APIRouter(prefix="/api/v1", tags=["verify"])


@router.get("/ping")
def ping() -> dict[str, str]:
    return {"message": "pong"}


@router.post("/verify")
async def verify(
    files: list[UploadFile] = File(..., description="One or more documents in a bundle"),
    declared_types: list[str] | None = Form(
        default=None,
        description="Optional per-file type hints, order-aligned with `files`",
    ),
) -> dict:
    """Ingest a bundle of documents and return a `VerificationReport` (contract §0)."""
    if not files:
        raise HTTPException(status_code=422, detail="No files uploaded.")
    if len(files) > MAX_FILES_PER_BUNDLE:
        raise HTTPException(
            status_code=422,
            detail=f"Too many files: {len(files)} > {MAX_FILES_PER_BUNDLE}.",
        )

    uploads: list[tuple[str, str, bytes, str | None]] = []
    for idx, upload in enumerate(files):
        data = await upload.read()
        if len(data) > MAX_FILE_BYTES:
            raise HTTPException(
                status_code=422,
                detail=f"'{upload.filename}' is {len(data)} bytes; limit is {MAX_FILE_BYTES}.",
            )
        declared = (
            declared_types[idx]
            if declared_types is not None and idx < len(declared_types)
            else None
        )
        uploads.append(
            (upload.filename or f"file_{idx}", upload.content_type or "", data, declared)
        )

    report = run_pipeline(uploads)

    storage.save_case(report)
    audit.record(
        report_id=report["report_id"],
        event_type="report_created",
        actor=None,
        detail={
            "document_count": report["bundle"]["document_count"],
            "status": report["status"],
        },
    )

    return report
