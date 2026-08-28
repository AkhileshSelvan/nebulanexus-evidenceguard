"""Turn an uploaded document (bytes) into a list of page images.

- Images (JPG/JPEG/PNG): decoded straight to a single-page list via Pillow.
- PDFs: rendered locally with PyMuPDF (no Poppler, no cloud service).

Every function returns plain ``PIL.Image`` objects in RGB (or L) mode. Decode
failures raise ``RasterizeError`` — the caller turns that into a warning, never
a crash.
"""

from __future__ import annotations

import io

from PIL import Image, ImageOps, UnidentifiedImageError

Image.MAX_IMAGE_PIXELS = 64_000_000  # ~8000x8000; guards against decompression bombs

# PDF render resolution. 200 DPI is a good accuracy/speed trade-off for OCR.
PDF_RENDER_DPI = 200
MAX_PDF_PAGES = 20  # keep a single document bounded


class RasterizeError(RuntimeError):
    """Raised when a source cannot be decoded into page images."""


IMAGE_MEDIA_TYPES = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/pjpeg": "jpg",
    "image/png": "png",
}
PDF_MEDIA_TYPES = {"application/pdf", "application/x-pdf", "application/acrobat"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".jpe", ".png"}
PDF_EXTENSIONS = {".pdf"}


def classify_source(media_type: str | None, filename: str | None) -> str:
    """Return "pdf", "image", or "unsupported" from the MIME type / extension."""
    mt = (media_type or "").split(";")[0].strip().lower()
    if mt in PDF_MEDIA_TYPES:
        return "pdf"
    if mt in IMAGE_MEDIA_TYPES:
        return "image"
    name = (filename or "").lower()
    dot = name.rfind(".")
    ext = name[dot:] if dot != -1 else ""
    if ext in PDF_EXTENSIONS:
        return "pdf"
    if ext in IMAGE_EXTENSIONS:
        return "image"
    return "unsupported"


def _sniff_bytes(data: bytes) -> str:
    if data[:5] == b"%PDF-":
        return "pdf"
    if data[:2] == b"\xff\xd8":  # JPEG SOI
        return "image"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image"
    return "unsupported"


def rasterize(
    data: bytes,
    *,
    media_type: str | None = None,
    filename: str | None = None,
) -> tuple[list[Image.Image], str]:
    """Decode ``data`` into ``(pages, source_kind)`` where source_kind is
    "image" or "pdf". Raises ``RasterizeError`` on unsupported / corrupt input."""
    if not data:
        raise RasterizeError("empty file")

    kind = classify_source(media_type, filename)
    if kind == "unsupported":
        kind = _sniff_bytes(data)  # trust the bytes over a wrong/missing MIME
    if kind == "unsupported":
        raise RasterizeError(
            f"unsupported media type {media_type!r} / filename {filename!r}; "
            "expected PDF, JPG, JPEG or PNG"
        )

    if kind == "pdf":
        return _rasterize_pdf(data), "pdf"
    return _rasterize_image(data), "image"


def _rasterize_image(data: bytes) -> list[Image.Image]:
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise RasterizeError(f"could not decode image: {exc}") from exc
    # Respect EXIF orientation before any further processing.
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("L", "RGB"):
        img = img.convert("RGB")
    return [img]


def _rasterize_pdf(data: bytes) -> list[Image.Image]:
    try:
        import pymupdf  # PyMuPDF >= 1.24
    except ImportError:  # pragma: no cover - older wheels expose "fitz"
        try:
            import fitz as pymupdf  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RasterizeError(
                "PDF support needs PyMuPDF ('pip install pymupdf')"
            ) from exc

    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:  # pymupdf raises its own error types
        raise RasterizeError(f"could not open PDF: {exc}") from exc

    pages: list[Image.Image] = []
    try:
        if doc.page_count == 0:
            raise RasterizeError("PDF has no pages")
        for index in range(min(doc.page_count, MAX_PDF_PAGES)):
            page = doc.load_page(index)
            pix = page.get_pixmap(dpi=PDF_RENDER_DPI, alpha=False)
            mode = "RGB" if pix.n >= 3 else "L"
            pages.append(Image.frombytes(mode, (pix.width, pix.height), pix.samples))
    finally:
        doc.close()

    if not pages:
        raise RasterizeError("PDF produced no rasterized pages")
    return pages
