"""Single-document image / file forensics.

Owner: Forensics developer.
Produces: ``Forensics`` (contract §3).

FOUNDATION STATUS: returns a clean, signal-free ``Forensics`` result.
No ELA / copy-move / noise analysis yet.
"""

from __future__ import annotations

from modules.contract import Forensics, Document

ENGINE = "stub-forensics"
ENGINE_VERSION = "0.0.0"


def analyze(document: Document, image_paths: list[str] | None = None) -> Forensics:
    """Run pixel/file-level manipulation checks on one document.

    Parameters
    ----------
    document:
        Normalized ``Document`` (contract §1).
    image_paths:
        Per-page raster image paths in page order (``None`` in the stub).

    Returns
    -------
    Forensics
        Contract §3. Stub returns ``signals = []`` and ``score = 0.0``.
    """
    return Forensics(
        engine=ENGINE,
        engine_version=ENGINE_VERSION,
        signals=[],
        score=0.0,
        summary="No forensic analysis performed (foundation stub).",
    )
