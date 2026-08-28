"""Light, robust image preprocessing for OCR.

Deliberately simple — no OpenCV, no numpy. Four steps:
  1. orientation  — rotate by Tesseract OSD's multiple-of-90 estimate (if it ran)
  2. grayscale    — OCR works on luminance
  3. contrast     — autocontrast clips the 1st/99th percentile
  4. resize       — upscale small scans toward ~300 DPI equivalent; cap the max edge

Returns the processed image plus a small record of what was done.
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageOps

from .engine import detect_orientation

# Target the long edge into this range. Tesseract likes ~1600-3000 px for a page.
MIN_LONG_EDGE = 1600
MAX_LONG_EDGE = 3500


@dataclass
class PreprocessResult:
    image: Image.Image
    rotation_applied: int  # 0 / 90 / 180 / 270
    resized_from: tuple[int, int] | None
    width: int
    height: int


def preprocess(
    image: Image.Image,
    *,
    handle_orientation: bool = True,
) -> PreprocessResult:
    work = image
    rotation = 0

    if handle_orientation:
        rotation = detect_orientation(work)
        if rotation in (90, 180, 270):
            # PIL rotates counter-clockwise for positive angles; OSD 'rotate' is
            # the clockwise angle to upright, so negate.
            work = work.rotate(-rotation, expand=True, fillcolor=255)

    if work.mode != "L":
        work = ImageOps.grayscale(work)

    work = ImageOps.autocontrast(work, cutoff=1)

    original_size = work.size
    resized_from: tuple[int, int] | None = None
    long_edge = max(work.size)
    if long_edge < MIN_LONG_EDGE:
        scale = MIN_LONG_EDGE / long_edge
    elif long_edge > MAX_LONG_EDGE:
        scale = MAX_LONG_EDGE / long_edge
    else:
        scale = 1.0
    if abs(scale - 1.0) > 1e-3:
        new_size = (max(1, round(work.width * scale)), max(1, round(work.height * scale)))
        resample = Image.LANCZOS if scale < 1.0 else Image.BICUBIC
        work = work.resize(new_size, resample=resample)
        resized_from = original_size

    return PreprocessResult(
        image=work,
        rotation_applied=rotation,
        resized_from=resized_from,
        width=work.width,
        height=work.height,
    )
