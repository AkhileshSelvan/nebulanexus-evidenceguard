"""Single-document image / file forensics.

Owner: Forensics developer.
Produces: ``Forensics`` (contract §3).

Runs real pixel-level and PDF-level manipulation checks on each document.
Does NOT make a fraud decision — returns structured evidence per the contract.
"""

from __future__ import annotations

import logging

from PIL import Image

from modules.contract import Document, Forensics, ForensicSignal

from .image_forensics import (
    detect_copy_move,
    detect_double_compression,
    detect_ela_hotspots,
    detect_noise_inconsistency,
)
from .normalization import load_pages, normalize_for_analysis
from .pdf_forensics import check_annotation_overlay, check_text_layer_mismatch

logger = logging.getLogger(__name__)

ENGINE = "evidenceguard-forensics"
ENGINE_VERSION = "0.2.0"

# Weights for rolling up individual signal scores into Forensics.score.
# Higher weight = more influence on the overall section score.
SIGNAL_WEIGHTS: dict[str, float] = {
    "ela_hotspot": 0.30,
    "noise_inconsistency": 0.20,
    "double_compression": 0.15,
    "copy_move": 0.15,
    "text_layer_mismatch": 0.10,
    "annotation_overlay": 0.10,
}


def analyze(
    document: Document,
    image_paths: list[str] | None = None,
    *,
    file_data: bytes | None = None,
) -> Forensics:
    """Run pixel/file-level manipulation checks on one document.

    Parameters
    ----------
    document:
        Normalized ``Document`` (contract §1).
    image_paths:
        Per-page raster image paths in page order.
    file_data:
        Raw file bytes (PDF or image). Needed for PDF-specific checks and
        as a fallback when *image_paths* are not available.

    Returns
    -------
    Forensics
        Contract §3. Returns real signals with scores, confidence, and regions.
        Never raises — returns empty signals on error.
    """
    signals: list[ForensicSignal] = []
    media_type = document.get("media_type", "application/octet-stream")
    is_pdf = media_type in {"application/pdf", "application/x-pdf"}

    # --- Load page images ------------------------------------------------- #
    pages: list[Image.Image] = []
    try:
        pages = load_pages(
            media_type=media_type,
            image_paths=image_paths,
            file_data=file_data,
        )
    except Exception as exc:
        logger.warning("Failed to load pages for forensics: %s", exc)

    # --- Image-level checks (per page) ------------------------------------ #
    for page_idx, page_img in enumerate(pages):
        try:
            normalized = normalize_for_analysis(page_img)
        except Exception as exc:
            logger.warning("Failed to normalize page %d: %s", page_idx + 1, exc)
            continue

        page_num = page_idx + 1

        # ELA
        try:
            ela_signal = detect_ela_hotspots(normalized)
            _set_pages(ela_signal, page_num)
            signals.append(ela_signal)
        except Exception as exc:
            logger.warning("ELA failed on page %d: %s", page_num, exc)

        # Noise inconsistency
        try:
            noise_signal = detect_noise_inconsistency(normalized)
            _set_pages(noise_signal, page_num)
            signals.append(noise_signal)
        except Exception as exc:
            logger.warning("Noise analysis failed on page %d: %s", page_num, exc)

        # Double compression
        try:
            dcomp_signal = detect_double_compression(normalized)
            _set_pages(dcomp_signal, page_num)
            signals.append(dcomp_signal)
        except Exception as exc:
            logger.warning("Double compression check failed on page %d: %s", page_num, exc)

        # Copy-move
        try:
            cm_signal = detect_copy_move(normalized)
            _set_pages(cm_signal, page_num)
            signals.append(cm_signal)
        except Exception as exc:
            logger.warning("Copy-move detection failed on page %d: %s", page_num, exc)

    # --- PDF-specific checks ---------------------------------------------- #
    if is_pdf and file_data:
        try:
            tlm_signal = check_text_layer_mismatch(file_data, pages)
            signals.append(tlm_signal)
        except Exception as exc:
            logger.warning("Text layer mismatch check failed: %s", exc)

        try:
            annot_signal = check_annotation_overlay(file_data)
            signals.append(annot_signal)
        except Exception as exc:
            logger.warning("Annotation overlay check failed: %s", exc)

    # --- Roll up ---------------------------------------------------------- #
    score = _rollup_score(signals)
    summary = _build_summary(signals, score)

    # If no pages could be loaded, return a clean but informative result
    if not signals:
        return Forensics(
            engine=ENGINE,
            engine_version=ENGINE_VERSION,
            signals=[],
            score=0.0,
            summary="No forensic analysis performed (no page images available).",
        )

    return Forensics(
        engine=ENGINE,
        engine_version=ENGINE_VERSION,
        signals=signals,
        score=score,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _set_pages(signal: ForensicSignal, page_num: int) -> None:
    """Set the page number on a signal and its regions."""
    signal["pages"] = [page_num]
    for region in signal.get("regions", []):
        region["page"] = page_num


def _rollup_score(signals: list[ForensicSignal]) -> float:
    """Compute the section-level score as a weighted combination.

    Uses weighted average of individual signal scores. Signals that didn't
    fire (passed=True) contribute 0.
    """
    if not signals:
        return 0.0

    total_weight = 0.0
    weighted_sum = 0.0

    for sig in signals:
        weight = SIGNAL_WEIGHTS.get(sig["id"], 0.1)
        weighted_sum += sig["score"] * weight
        total_weight += weight

    if total_weight == 0:
        return 0.0

    return round(min(100.0, weighted_sum / total_weight), 1)


def _build_summary(signals: list[ForensicSignal], score: float) -> str:
    """Build a human-readable summary of the forensic findings."""
    failed = [s for s in signals if not s["passed"]]

    if not failed:
        return "No manipulation signals detected."

    n = len(failed)
    labels = [s["label"] for s in failed[:3]]
    label_str = ", ".join(labels)
    if n > 3:
        label_str += f", and {n - 3} more"

    return f"{n} signal(s) flagged: {label_str}. Overall concern score: {score}/100."
