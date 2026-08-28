"""Load and normalize page images for forensic analysis.

Self-contained page-loading so the forensics module stays independent of
``modules/ocr`` (per project rule 4: no cross-module imports).

Supports JPEG, PNG (via Pillow) and PDF (via PyMuPDF).
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

# Cap to prevent decompression bombs
Image.MAX_IMAGE_PIXELS = 64_000_000

# PDF rendering resolution — 200 DPI balances quality and speed
PDF_RENDER_DPI = 200
MAX_PDF_PAGES = 20

# Long-edge limits for forensic analysis images
MAX_ANALYSIS_EDGE = 4000
MIN_ANALYSIS_EDGE = 800


class NormalizationError(RuntimeError):
    """Raised when a source cannot be decoded into page images."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_pages(
    *,
    media_type: str,
    image_paths: list[str] | None = None,
    file_data: bytes | None = None,
) -> list[Image.Image]:
    """Load page images for analysis.

    Tries *image_paths* first (pre-rasterized pages from the orchestrator),
    then falls back to decoding *file_data* directly.

    Returns a list of PIL Images in RGB mode, one per page.
    """
    pages: list[Image.Image] = []

    # 1) Try loading from pre-rasterized paths
    if image_paths:
        for p in image_paths:
            path = Path(p)
            if path.is_file():
                try:
                    img = Image.open(path)
                    img.load()
                    pages.append(_to_rgb(img))
                except (UnidentifiedImageError, OSError):
                    pass  # skip unreadable paths
    if pages:
        return pages

    # 2) Decode from raw bytes
    if file_data:
        kind = _classify(media_type, file_data)
        if kind == "pdf":
            return _rasterize_pdf(file_data)
        if kind == "image":
            return _rasterize_image(file_data)

    return []


def normalize_for_analysis(image: Image.Image) -> Image.Image:
    """Prepare a page image for forensic analysis.

    - Converts to RGB
    - Applies EXIF transpose
    - Caps the long edge at MAX_ANALYSIS_EDGE
    - Upscales very small images to MIN_ANALYSIS_EDGE
    """
    work = _to_rgb(image)
    work = ImageOps.exif_transpose(work) or work

    long_edge = max(work.size)
    if long_edge > MAX_ANALYSIS_EDGE:
        scale = MAX_ANALYSIS_EDGE / long_edge
    elif long_edge < MIN_ANALYSIS_EDGE:
        scale = MIN_ANALYSIS_EDGE / long_edge
    else:
        scale = 1.0

    if abs(scale - 1.0) > 1e-3:
        new_w = max(1, round(work.width * scale))
        new_h = max(1, round(work.height * scale))
        resample = Image.LANCZOS if scale < 1.0 else Image.BICUBIC
        work = work.resize((new_w, new_h), resample=resample)

    return work


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _to_rgb(img: Image.Image) -> Image.Image:
    if img.mode == "RGB":
        return img
    return img.convert("RGB")


def _classify(media_type: str, data: bytes) -> str:
    """Return 'pdf', 'image', or 'unsupported'."""
    mt = (media_type or "").split(";")[0].strip().lower()
    if mt in {"application/pdf", "application/x-pdf"}:
        return "pdf"
    if mt.startswith("image/"):
        return "image"
    # Sniff magic bytes
    if data[:5] == b"%PDF-":
        return "pdf"
    if data[:2] == b"\xff\xd8":  # JPEG SOI
        return "image"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image"
    return "unsupported"


def _rasterize_image(data: bytes) -> list[Image.Image]:
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise NormalizationError(f"could not decode image: {exc}") from exc
    img = ImageOps.exif_transpose(img) or img
    return [_to_rgb(img)]


def _rasterize_pdf(data: bytes) -> list[Image.Image]:
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf  # type: ignore[no-redef]
        except ImportError as exc:
            raise NormalizationError(
                "PDF support needs PyMuPDF ('pip install pymupdf')"
            ) from exc

    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise NormalizationError(f"could not open PDF: {exc}") from exc

    pages: list[Image.Image] = []
    try:
        for idx in range(min(doc.page_count, MAX_PDF_PAGES)):
            page = doc.load_page(idx)
            pix = page.get_pixmap(dpi=PDF_RENDER_DPI, alpha=False)
            mode = "RGB" if pix.n >= 3 else "L"
            img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
            pages.append(_to_rgb(img))
    finally:
        doc.close()

    return pages
