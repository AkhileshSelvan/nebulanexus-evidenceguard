"""Text & field extraction.

Owner: OCR developer.
Produces: ``Extraction`` (contract §2).

FOUNDATION STATUS: returns a valid, empty-ish ``Extraction`` so the pipeline
runs end to end. No real OCR yet — that is a later checkpoint.
"""

from __future__ import annotations

from modules.contract import Extraction, Document

ENGINE = "stub-ocr"
ENGINE_VERSION = "0.0.0"


def extract(document: Document, image_paths: list[str] | None = None) -> Extraction:
    """Extract text and structured fields from one normalized document.

    Parameters
    ----------
    document:
        The normalized ``Document`` (contract §1) from the backend.
    image_paths:
        Absolute paths to the per-page raster images the backend prepared,
        in page order. ``None`` / empty in the foundation stub.

    Returns
    -------
    Extraction
        Contract §2. In the stub, ``fields`` and ``tables`` are empty and
        confidences are ``0.0``.
    """
    return Extraction(
        engine=ENGINE,
        engine_version=ENGINE_VERSION,
        language=None,
        full_text="",
        text_confidence=0.0,
        fields=[],
        tables=[],
    )
