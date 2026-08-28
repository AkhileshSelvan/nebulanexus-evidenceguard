"""Cross-document consistency checks.

Owner: Consistency developer.
Produces: ``Consistency`` (contract §5).

FOUNDATION STATUS: returns an empty-but-valid ``Consistency`` block.
No field matching / date-ordering / arithmetic yet.
"""

from __future__ import annotations

from modules.contract import Consistency, Document, Extraction

ENGINE = "stub-consistency"
ENGINE_VERSION = "0.0.0"


def check_consistency(
    documents: list[Document],
    extractions: list[Extraction],
) -> Consistency:
    """Compare the extracted fields of every document in a bundle.

    Parameters
    ----------
    documents:
        All normalized documents in the bundle (contract §1), order-aligned
        with ``extractions``.
    extractions:
        The ``Extraction`` (contract §2) for each document, same order.

    Returns
    -------
    Consistency
        Contract §5. Stub returns ``checks = []`` and ``score = 0.0``.
    """
    return Consistency(
        engine=ENGINE,
        engine_version=ENGINE_VERSION,
        checks=[],
        cross_references=[],
        score=0.0,
        summary="No consistency checks performed (foundation stub).",
    )
