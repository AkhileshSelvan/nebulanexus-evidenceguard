"""Fixtures for modules/ocr tests.

Everything here builds *real* image/PDF bytes with real rendered text (via
PIL + a real TrueType font, or PyMuPDF for PDFs) so the tests below exercise
the actual OCR pipeline end to end rather than mocking it away.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image, ImageDraw, ImageFont

from modules.contract import Document

# A handful of common install locations across the Linux distros CI is likely
# to run on. If none exist, font-dependent tests are skipped with a clear
# reason rather than failing on an environment difference.
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def _find_font(size: int) -> ImageFont.FreeTypeFont | None:
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return None


@pytest.fixture(scope="session")
def ocr_font_or_skip() -> ImageFont.FreeTypeFont:
    font = _find_font(32)
    if font is None:
        pytest.skip("no TrueType font available in this environment for OCR fixtures")
    return font


def render_text_png(lines: list[str], font: ImageFont.FreeTypeFont) -> bytes:
    """Render ``lines`` onto a white page and return PNG bytes."""
    width, line_height = 1000, 50
    height = max(200, line_height * (len(lines) + 2))
    img = Image.new("L", (width, height), color=255)
    draw = ImageDraw.Draw(img)
    y = 20
    for line in lines:
        draw.text((20, y), line, fill=0, font=font)
        y += line_height
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_text_pdf(pages: list[list[str]]) -> bytes:
    """Build a real multi-page PDF with real (vector, not rasterized) text."""
    import pymupdf

    doc = pymupdf.open()
    for lines in pages:
        page = doc.new_page(width=612, height=792)  # US letter
        y = 72
        for line in lines:
            page.insert_text((72, y), line, fontsize=16)
            y += 24
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture
def make_document():
    def _make(filename: str, media_type: str, byte_size: int = 0) -> Document:
        return Document(
            id="doc_test0001",
            bundle_id="bnd_test0001",
            filename=filename,
            media_type=media_type,
            byte_size=byte_size,
            sha256="0" * 64,
            page_count=1,
            declared_type=None,
            detected_type=None,
            pages=[],
            received_at="2026-08-28T00:00:00Z",
        )

    return _make
