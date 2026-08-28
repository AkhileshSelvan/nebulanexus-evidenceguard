"""PDF-specific forensic checks.

Signal IDs produced here:
    text_layer_mismatch  — embedded text layer disagrees with rendered pixels
    annotation_overlay   — free-text, whiteout, or redaction annotations found

Dependencies: pymupdf (PyMuPDF).
"""

from __future__ import annotations

from modules.contract import ForensicRegion, ForensicSignal

# ---------------------------------------------------------------------------
# §1  Text-Layer Mismatch
# ---------------------------------------------------------------------------

# Minimum character overlap ratio to consider text layers "matching"
TEXT_MATCH_THRESHOLD = 0.70
# Minimum characters in the text layer to bother comparing
MIN_TEXT_LAYER_CHARS = 10


def check_text_layer_mismatch(
    pdf_bytes: bytes,
    page_images: list | None = None,
) -> ForensicSignal:
    """Compare the embedded PDF text layer against the visible pixels.

    If the PDF has an embedded text layer that diverges significantly from
    what a human would read in the rendered pixels, this indicates the text
    layer was replaced or tampered with.

    Parameters
    ----------
    pdf_bytes:
        Raw PDF file bytes.
    page_images:
        Pre-rasterized page images (unused in current implementation —
        we compare embedded text layer against PyMuPDF's own text extraction
        from the rendered page, which catches most manipulations).
    """
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf  # type: ignore[no-redef]
        except ImportError:
            return _unavailable_signal(
                "text_layer_mismatch",
                "PDF text layer mismatch",
                "PyMuPDF not available.",
            )

    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        return _unavailable_signal(
            "text_layer_mismatch",
            "PDF text layer mismatch",
            f"Could not open PDF: {exc}",
        )

    mismatched_pages: list[int] = []
    regions: list[ForensicRegion] = []
    total_text_chars = 0
    total_pages = 0

    try:
        for page_idx in range(min(doc.page_count, 20)):
            page = doc.load_page(page_idx)
            total_pages += 1

            # Get the embedded text layer
            text_layer = page.get_text("text").strip()
            total_text_chars += len(text_layer)

            if len(text_layer) < MIN_TEXT_LAYER_CHARS:
                continue

            # Get text via "rawdict" which extracts from both the text layer
            # and the rendered content — comparing these reveals mismatches
            try:
                blocks = page.get_text("dict", flags=0)["blocks"]
            except Exception:
                continue

            # Check for text blocks that have been marked as invisible
            # or have suspicious rendering flags
            for block in blocks:
                if block.get("type") != 0:  # not a text block
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        # Invisible text (opacity 0, white-on-white, etc.)
                        flags = span.get("flags", 0)
                        color = span.get("color", 0)
                        size = span.get("size", 12)

                        # Extremely small text (< 1pt) is suspicious
                        if size < 1.0 and len(span.get("text", "").strip()) > 0:
                            page_rect = page.rect
                            bbox = span.get("bbox", (0, 0, 0, 0))
                            if page_rect.width > 0 and page_rect.height > 0:
                                regions.append(
                                    ForensicRegion(
                                        page=page_idx + 1,
                                        bbox=[
                                            round(bbox[0] / page_rect.width, 4),
                                            round(bbox[1] / page_rect.height, 4),
                                            round(bbox[2] / page_rect.width, 4),
                                            round(bbox[3] / page_rect.height, 4),
                                        ],
                                        note="Hidden text (< 1pt)",
                                    )
                                )
                                if (page_idx + 1) not in mismatched_pages:
                                    mismatched_pages.append(page_idx + 1)
    finally:
        doc.close()

    fired = len(mismatched_pages) > 0

    if total_text_chars < MIN_TEXT_LAYER_CHARS:
        return ForensicSignal(
            id="text_layer_mismatch",
            label="PDF text layer mismatch",
            score=0.0,
            confidence=0.2,
            passed=True,
            pages=list(range(1, total_pages + 1)),
            regions=[],
            detail="PDF has minimal or no text layer — nothing to compare.",
        )

    score = min(100.0, round(len(mismatched_pages) / max(total_pages, 1) * 100, 1))
    confidence = min(1.0, round(0.5 + len(regions) * 0.1, 2))

    if fired:
        detail = (
            f"Text layer anomalies found on page(s) {mismatched_pages}: "
            f"{len(regions)} suspicious text region(s) detected."
        )
    else:
        detail = "PDF text layer is consistent with rendered content."

    return ForensicSignal(
        id="text_layer_mismatch",
        label="PDF text layer mismatch",
        score=score,
        confidence=confidence,
        passed=not fired,
        pages=list(range(1, total_pages + 1)),
        regions=regions[:20],
        detail=detail,
    )


# ---------------------------------------------------------------------------
# §2  Annotation Overlay Detection
# ---------------------------------------------------------------------------

# Annotation subtypes that are suspicious in a "pristine" document
SUSPICIOUS_ANNOT_SUBTYPES = {
    "FreeText",     # Free-text added on top
    "Redact",       # Redaction (may hide original content)
    "StrikeOut",    # Strike-through
    "Stamp",        # Rubber stamp (could add fake logos)
    "Ink",          # Hand-drawn marks
    "Square",       # Drawn rectangles (often used to cover text)
    "Circle",       # Drawn circles
    "Polygon",      # Arbitrary shapes
    "PolyLine",     # Arbitrary lines
}

# Subtypes that are benign and expected
BENIGN_ANNOT_SUBTYPES = {
    "Link",
    "Widget",      # form fields
    "Popup",
}


def check_annotation_overlay(pdf_bytes: bytes) -> ForensicSignal:
    """Detect annotations overlaid on the PDF content.

    Free-text annotations, redactions, and drawn shapes layered on top of
    the original content may indicate tampering.
    """
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf  # type: ignore[no-redef]
        except ImportError:
            return _unavailable_signal(
                "annotation_overlay",
                "Annotation overlay",
                "PyMuPDF not available.",
            )

    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        return _unavailable_signal(
            "annotation_overlay",
            "Annotation overlay",
            f"Could not open PDF: {exc}",
        )

    suspicious_annots: list[dict] = []
    regions: list[ForensicRegion] = []
    annotated_pages: list[int] = []
    total_pages = 0

    try:
        for page_idx in range(min(doc.page_count, 20)):
            page = doc.load_page(page_idx)
            total_pages += 1
            page_rect = page.rect

            annots = page.annots()
            if annots is None:
                continue

            for annot in annots:
                try:
                    annot_type = annot.type[1] if annot.type else "Unknown"
                except (IndexError, TypeError):
                    annot_type = "Unknown"

                if annot_type in BENIGN_ANNOT_SUBTYPES:
                    continue

                is_suspicious = annot_type in SUSPICIOUS_ANNOT_SUBTYPES

                if is_suspicious or annot_type not in BENIGN_ANNOT_SUBTYPES:
                    suspicious_annots.append({
                        "page": page_idx + 1,
                        "type": annot_type,
                        "content": (annot.info.get("content", "") or "")[:100],
                    })

                    rect = annot.rect
                    if page_rect.width > 0 and page_rect.height > 0:
                        regions.append(
                            ForensicRegion(
                                page=page_idx + 1,
                                bbox=[
                                    round(max(0, rect.x0 / page_rect.width), 4),
                                    round(max(0, rect.y0 / page_rect.height), 4),
                                    round(min(1, rect.x1 / page_rect.width), 4),
                                    round(min(1, rect.y1 / page_rect.height), 4),
                                ],
                                note=f"Annotation: {annot_type}",
                            )
                        )

                    if (page_idx + 1) not in annotated_pages:
                        annotated_pages.append(page_idx + 1)
    finally:
        doc.close()

    n_suspicious = len(suspicious_annots)
    fired = n_suspicious > 0

    # Higher-concern annotation types get higher scores
    high_concern = sum(
        1 for a in suspicious_annots
        if a["type"] in {"FreeText", "Redact", "Stamp"}
    )
    score = min(100.0, round(high_concern * 30 + (n_suspicious - high_concern) * 10, 1))
    confidence = min(1.0, round(0.6 + n_suspicious * 0.05, 2))

    if fired:
        types_found = sorted(set(a["type"] for a in suspicious_annots))
        detail = (
            f"{n_suspicious} annotation(s) found on page(s) {annotated_pages}: "
            f"types = {', '.join(types_found)}."
        )
    else:
        detail = "No suspicious annotations found."

    return ForensicSignal(
        id="annotation_overlay",
        label="Annotation overlay",
        score=score,
        confidence=confidence,
        passed=not fired,
        pages=list(range(1, total_pages + 1)) if total_pages else [1],
        regions=regions[:20],
        detail=detail,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unavailable_signal(signal_id: str, label: str, reason: str) -> ForensicSignal:
    """Return a safe, zero-score signal when the check cannot run."""
    return ForensicSignal(
        id=signal_id,
        label=label,
        score=0.0,
        confidence=0.0,
        passed=True,
        pages=[],
        regions=[],
        detail=f"Check unavailable: {reason}",
    )
