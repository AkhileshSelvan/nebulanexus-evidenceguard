"""Risk module — owns §6 (`risk`), §7 (`recommendation`), §8 (`explanation`)."""

from .scorer import score_document, score_bundle, recommend, explain

__all__ = ["score_document", "score_bundle", "recommend", "explain"]
