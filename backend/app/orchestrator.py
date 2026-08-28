"""Wire the analysis modules together into a VerificationReport.

The backend is the *only* place that imports from ``modules/``. Everything here
follows ``docs/API_CONTRACT.md``.

FOUNDATION STATUS: ingest is real (hash, size, media type). Page rasterization
is not done yet, so ``document.pages`` is a single synthetic entry and modules
receive no image paths. Modules return contract-shaped placeholder data.
"""

from __future__ import annotations

import hashlib
import sys
import uuid
from pathlib import Path

# --- make the repo-root ``modules`` package importable ---------------------- #
# backend/app/orchestrator.py -> parents[2] == repo root
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from modules.consistency import check_consistency  # noqa: E402
from modules.contract import (  # noqa: E402
    Document,
    ReportBundle,
    ReportDocumentEntry,
    VerificationReport,
)
from modules.forensics import analyze, extract_metadata  # noqa: E402
from modules.ocr import extract  # noqa: E402
from modules.risk import explain, recommend, score_bundle, score_document  # noqa: E402

from app.timeutil import now_iso


def _short_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def build_document(
    *,
    bundle_id: str,
    filename: str,
    media_type: str,
    data: bytes,
    declared_type: str | None,
) -> Document:
    """Normalize one uploaded file into a contract §1 ``Document``."""
    return Document(
        id=_short_id("doc"),
        bundle_id=bundle_id,
        filename=filename,
        media_type=media_type or "application/octet-stream",
        byte_size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        page_count=1,  # TODO: real page count once rasterization lands
        declared_type=declared_type,
        detected_type=None,  # TODO: type sniffing
        pages=[
            {
                "page_number": 1,
                "width": 0,
                "height": 0,
                "image_ref": f"{filename}#p1",
            }
        ],
        received_at=now_iso(),
    )


def run_pipeline(
    uploads: list[tuple[str, str, bytes, str | None]],
) -> VerificationReport:
    """Run the full verification pipeline over one bundle of uploaded files.

    Parameters
    ----------
    uploads:
        List of ``(filename, media_type, bytes, declared_type)`` tuples.

    Returns
    -------
    VerificationReport
        Contract §0. In the foundation every module returns placeholder data,
        so the report is structurally complete but analytically empty.
    """
    bundle_id = _short_id("bnd")

    documents: list[Document] = [
        build_document(
            bundle_id=bundle_id,
            filename=name,
            media_type=mtype,
            data=data,
            declared_type=dtype,
        )
        for (name, mtype, data, dtype) in uploads
    ]

    # --- per-document stages ---------------------------------------------- #
    entries: list[ReportDocumentEntry] = []
    extractions = []
    for doc in documents:
        extraction = extract(doc, image_paths=[])
        forensics = analyze(doc, image_paths=[])
        metadata = extract_metadata(doc, file_path=None)
        doc_risk = score_document(doc["id"], forensics, metadata)

        extractions.append(extraction)
        entries.append(
            ReportDocumentEntry(
                document=doc,
                extraction=extraction,
                forensics=forensics,
                metadata=metadata,
                risk=doc_risk,
            )
        )

    # --- bundle-level stages -------------------------------------------- #
    consistency = check_consistency(documents, extractions)
    document_risks = [e["risk"] for e in entries]
    bundle_risk = score_bundle(bundle_id, document_risks, consistency)
    recommendation = recommend(bundle_risk)
    explanation = explain(bundle_risk, document_risks, consistency)

    return VerificationReport(
        report_id=_short_id("rep"),
        created_at=now_iso(),
        status="complete",
        bundle=ReportBundle(bundle_id=bundle_id, document_count=len(documents)),
        documents=entries,
        consistency=consistency,
        risk=bundle_risk,
        recommendation=recommendation,
        explanation=explanation,
        errors=[],
    )
