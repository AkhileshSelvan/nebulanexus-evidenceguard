"""File-history / metadata plausibility.

Owner: Forensics developer (may be spun out into its own module later —
that's why it has a separate entry point and contract section).
Produces: ``Metadata`` (contract §4).

FOUNDATION STATUS: returns an empty-but-valid ``Metadata`` block. Real
PDF/EXIF parsing (pikepdf, exifread, hachoir, …) comes later.
"""

from __future__ import annotations

from modules.contract import Metadata, MetadataDerived, Document

ENGINE = "stub-metadata"
ENGINE_VERSION = "0.0.0"


def extract_metadata(document: Document, file_path: str | None = None) -> Metadata:
    """Extract and sanity-check a document's embedded metadata.

    Parameters
    ----------
    document:
        Normalized ``Document`` (contract §1).
    file_path:
        Absolute path to the *original* uploaded bytes (``None`` in the stub).

    Returns
    -------
    Metadata
        Contract §4. Stub returns empty ``raw`` / ``signals`` and ``score = 0.0``.
    """
    container = _container_for_media_type(document["media_type"])
    return Metadata(
        engine=ENGINE,
        engine_version=ENGINE_VERSION,
        container=container,
        raw={},
        derived=MetadataDerived(
            created_at=None,
            modified_at=None,
            producer=None,
            creator_tool=None,
            has_gps=False,
            software_edits=[],
        ),
        signals=[],
        score=0.0,
        summary="No metadata extracted (foundation stub).",
    )


def _container_for_media_type(media_type: str) -> str:
    mapping = {
        "application/pdf": "pdf",
        "image/jpeg": "jpeg",
        "image/png": "png",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    }
    return mapping.get(media_type, "unknown")
