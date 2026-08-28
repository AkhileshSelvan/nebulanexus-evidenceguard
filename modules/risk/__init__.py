"""Risk module — owns §6 (`risk`), §7 (`recommendation`), §8 (`explanation`).

A transparent, deterministic **risk-triage** engine. It fuses evidence from the
OCR, forensics, metadata and consistency sections into a bounded 0-100 score
with exactly-additive contributions. It does not prove a document genuine and it
does not prove one fraudulent — it ranks how much human attention a bundle needs.

    from modules.risk import score_document, score_bundle, recommend, explain
"""

from .scorer import (
    ENGINE,
    ENGINE_VERSION,
    MODEL_METHOD,
    REASON_CODES,
    SOURCE_PROBABILITY_CEILING,
    SOURCE_WEIGHTS,
    UNREPORTED_CONFIDENCE,
    explain,
    recommend,
    score_bundle,
    score_document,
)

__all__ = [
    "score_document",
    "score_bundle",
    "recommend",
    "explain",
    "SOURCE_WEIGHTS",
    "SOURCE_PROBABILITY_CEILING",
    "UNREPORTED_CONFIDENCE",
    "REASON_CODES",
    "ENGINE",
    "ENGINE_VERSION",
    "MODEL_METHOD",
]
