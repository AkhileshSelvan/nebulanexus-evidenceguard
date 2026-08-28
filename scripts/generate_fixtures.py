"""Generate synthetic demo cases for EvidenceGuard forensic analysis.

Creates a suite of test documents across five categories:
  1. genuine_clean   — should pass all forensic checks
  2. tampered_ela    — triggers ELA (spliced high-frequency patch)
  3. tampered_copymove — triggers copy-move (duplicated region)
  4. low_quality_scan — triggers noise inconsistency (smooth splice on noisy bg)
  5. tampered_metadata — PDF with future dates & image-editor producer
  6. contradictory_bundle — two PDFs whose metadata contradict each other

Run from the repo root:
    python scripts/generate_fixtures.py

Produces files in data/demo/cases/.
"""

import io
import os
from datetime import datetime, timedelta, timezone

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _natural_scene(w: int = 800, h: int = 600, seed: int = 12345) -> Image.Image:
    """Create a natural-looking scene with spatially varying content.

    Uses smooth gradients and organic shapes so that:
    - Blocks are unique (no copy-move false positives)
    - Noise variance is spatially consistent
    - No periodic histogram structure (no double-compression FP)
    """
    rng = np.random.default_rng(seed)

    # Smooth gradient background
    ys = np.linspace(0, 1, h)[:, None]
    xs = np.linspace(0, 1, w)[None, :]
    r = (180 + 60 * np.sin(xs * 3.5 + 0.5) * np.cos(ys * 2.1)).astype(np.float64)
    g = (140 + 80 * np.cos(xs * 2.7 + 1.0) * np.sin(ys * 3.3 + 0.7)).astype(np.float64)
    b = (120 + 70 * np.sin(xs * 4.1 + ys * 1.9)).astype(np.float64)
    arr = np.stack([r, g, b], axis=2)
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)

    # Add soft ellipses for variety
    draw = ImageDraw.Draw(img)
    for _ in range(15):
        cx, cy = rng.integers(0, w), rng.integers(0, h)
        rx, ry = rng.integers(20, 80), rng.integers(20, 80)
        color = tuple(rng.integers(50, 220, 3).tolist())
        draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=color)

    # Blur to smooth out hard edges (reduces ELA false positives)
    img = img.filter(ImageFilter.GaussianBlur(radius=2))
    return img


# ---------------------------------------------------------------------------
# Fixture generators
# ---------------------------------------------------------------------------


def gen_genuine_clean():
    """A clean image with natural content, saved once at Q95.

    Expected: all forensic signals should PASS (low scores).
    """
    img = _natural_scene()
    img.save("data/demo/cases/genuine_clean.jpg", "JPEG", quality=95)


def gen_tampered_ela():
    """An image with a spliced patch that triggers ELA.

    Strategy: degrade the base to Q=50 (smooth, low-frequency) and then
    paste a patch of random noise (high-frequency). Save at Q=95.

    When ELA resaves at Q=90:
    - Smooth base: Q=95→Q=90 barely changes it → low ELA diff
    - Noisy patch: Q=95→Q=90 alters high-frequency info → high ELA diff
    """
    base = _natural_scene()

    # Degrade base to remove all high-frequency detail
    buf = io.BytesIO()
    base.save(buf, "JPEG", quality=50)
    buf.seek(0)
    base = Image.open(buf)
    base.load()

    # Fresh patch with random noise (high-frequency content)
    rng = np.random.default_rng(99999)
    patch_arr = rng.integers(0, 256, (180, 250, 3), dtype=np.uint8)
    patch = Image.fromarray(patch_arr)

    base.paste(patch, (280, 200))
    base.save("data/demo/cases/tampered_ela.jpg", "JPEG", quality=95)


def gen_tampered_copymove():
    """An image with a genuinely duplicated region to trigger copy-move.

    Copies a textured (non-uniform) region to a distant location within
    the same image. The copy-move detector should find matching blocks.
    """
    img = _natural_scene(seed=54321)

    # Copy a non-uniform region (std >> 8 to pass the uniform filter)
    # Align to 16x16 boundaries so JPEG compression artifacts match perfectly
    src_box = (64, 64, 256, 256)  # 192×192 region
    region = img.crop(src_box)

    # Duplicate it to multiple distant locations (also 16-aligned)
    for dst in [(496, 352), (496, 64), (64, 352)]:
        img.paste(region, dst)

    img.save("data/demo/cases/tampered_copymove.jpg", "JPEG", quality=95)


def gen_low_quality_scan():
    """An image with a smooth spliced patch on noisy background.

    The background has strong Gaussian noise. The patch is perfectly smooth.
    This creates a stark noise-variance inconsistency.
    """
    base = _natural_scene()
    arr = np.array(base, dtype=np.float32)
    noise = np.random.default_rng(42).normal(0, 25, arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    noisy = Image.fromarray(arr)

    # Smooth patch — zero noise variance
    patch = Image.new("RGB", (300, 200), color=(180, 180, 180))
    draw = ImageDraw.Draw(patch)
    draw.text((20, 80), "SPLICED CONTENT", fill=(0, 0, 0))
    noisy.paste(patch, (250, 200))

    noisy.save("data/demo/cases/low_quality_scan.jpg", "JPEG", quality=95)


def gen_tampered_metadata_pdf():
    """A PDF with future timestamps and image-editor producer metadata.

    Signals expected to fail:
    - future_timestamp
    - editor_is_image_tool
    - producer_mismatch_for_issuer (when declared as bank_statement)
    """
    import pikepdf

    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(612, 792))

    with pdf.open_metadata() as meta:
        meta["xmp:CreatorTool"] = "Adobe Photoshop CC 2019"

    future = datetime.now(timezone.utc) + timedelta(days=30)
    fut_str = future.strftime("D:%Y%m%d%H%M%S+00'00'")

    docinfo = pdf.docinfo
    docinfo["/CreationDate"] = fut_str
    docinfo["/ModDate"] = fut_str
    docinfo["/Producer"] = "Adobe Photoshop CC 2019"
    docinfo["/Creator"] = "Photoshop"

    pdf.save("data/demo/cases/tampered_metadata.pdf")


def gen_contradictory_metadata_pdf():
    """A PDF where modification date is BEFORE creation date.

    Also has mismatched timezones (created UTC, modified UTC+5).
    Signals expected to fail:
    - modified_after_creation (modified before created)
    - timezone_mismatch
    """
    import pikepdf

    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(612, 792))

    # Created "recently", but modified "yesterday" — impossible
    now = datetime.now(timezone.utc)
    created_str = now.strftime("D:%Y%m%d%H%M%S+00'00'")
    yesterday = now - timedelta(days=1)
    modified_str = yesterday.strftime("D:%Y%m%d%H%M%S+05'30'")  # different TZ

    docinfo = pdf.docinfo
    docinfo["/CreationDate"] = created_str
    docinfo["/ModDate"] = modified_str
    docinfo["/Producer"] = "wkhtmltopdf 0.12.6"
    docinfo["/Creator"] = "wkhtmltopdf"

    pdf.save("data/demo/cases/contradictory_metadata.pdf")


def gen_clean_metadata_pdf():
    """A clean PDF with consistent, plausible metadata.

    Expected: all metadata signals should PASS.
    """
    import pikepdf

    pdf = pikepdf.Pdf.new()
    pdf.add_blank_page(page_size=(612, 792))

    now = datetime.now(timezone.utc)
    created = now - timedelta(days=2)
    created_str = created.strftime("D:%Y%m%d%H%M%S+00'00'")
    # Modified 1 hour after creation
    modified = created + timedelta(hours=1)
    modified_str = modified.strftime("D:%Y%m%d%H%M%S+00'00'")

    docinfo = pdf.docinfo
    docinfo["/CreationDate"] = created_str
    docinfo["/ModDate"] = modified_str
    docinfo["/Producer"] = "wkhtmltopdf 0.12.6"
    docinfo["/Creator"] = "wkhtmltopdf"

    pdf.save("data/demo/cases/clean_metadata.pdf")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def generate_fixtures():
    os.makedirs("data/demo/cases", exist_ok=True)
    gen_genuine_clean()
    gen_tampered_ela()
    gen_tampered_copymove()
    gen_low_quality_scan()
    gen_tampered_metadata_pdf()
    gen_contradictory_metadata_pdf()
    gen_clean_metadata_pdf()
    print("All fixtures generated in data/demo/cases/")


if __name__ == "__main__":
    generate_fixtures()
