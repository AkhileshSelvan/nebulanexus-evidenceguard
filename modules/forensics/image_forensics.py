"""Pixel-level image forensic analysis.

All functions are pure: image in → result out. No network calls, no state.
Dependencies: Pillow (already present), numpy.

Signal IDs produced here:
    ela_hotspot          — Error-Level Analysis resave artifacts
    noise_inconsistency  — local noise variance outliers across blocks
    double_compression   — periodic peaks in DCT coefficient histograms
    copy_move            — duplicated regions within the same page
"""

from __future__ import annotations

import io
import math
from typing import Any

import numpy as np
from PIL import Image, ImageFilter

from modules.contract import ForensicRegion, ForensicSignal

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ELA_RESAVE_QUALITY = 90
ELA_BLOCK_SIZE = 16        # pixels per grid cell for hot-spot detection
ELA_THRESHOLD = 8          # mean per-pixel raw diff in a block to flag
ELA_MIN_BLOCKS = 3         # minimum hot blocks to fire the signal

NOISE_BLOCK_SIZE = 32      # pixels per block for noise variance
NOISE_ZSCORE_THRESH = 2.0  # blocks with σ this far from the mean

COPY_MOVE_BLOCK = 16       # block size for copy-move matching
COPY_MOVE_HASH_BITS = 64   # bits in perceptual hash of each block
COPY_MOVE_MIN_MATCHES = 15 # minimum matching block-pairs to fire

DCT_HIST_BINS = 256        # bins for the DCT coefficient histogram
DCT_PERIOD_THRESH = 0.25   # normalized peak-to-average to flag


# ---------------------------------------------------------------------------
# §1  Error-Level Analysis (ELA)
# ---------------------------------------------------------------------------


def compute_ela(
    image: Image.Image,
    quality: int = ELA_RESAVE_QUALITY,
) -> tuple[Image.Image, float, float]:
    """Resave *image* as JPEG at *quality* and return the absolute difference.

    Returns (ela_image, max_diff, mean_diff) where ela_image is a grayscale
    PIL Image and max_diff/mean_diff are scalar pixel-value statistics.
    """
    buf = io.BytesIO()
    rgb = image.convert("RGB") if image.mode != "RGB" else image
    rgb.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    resaved = Image.open(buf)
    resaved.load()

    orig_arr = np.asarray(rgb, dtype=np.float32)
    re_arr = np.asarray(resaved, dtype=np.float32)
    diff = np.abs(orig_arr - re_arr)

    # Collapse channels to a single luminance-diff
    if diff.ndim == 3:
        diff = diff.mean(axis=2)

    max_diff = float(diff.max())
    mean_diff = float(diff.mean())

    # Scale to [0, 255] for visualization
    if max_diff > 0:
        ela_vis = (diff / max_diff * 255).astype(np.uint8)
    else:
        ela_vis = diff.astype(np.uint8)

    ela_image = Image.fromarray(ela_vis, mode="L")
    return ela_image, max_diff, mean_diff


def detect_ela_hotspots(
    image: Image.Image,
    quality: int = ELA_RESAVE_QUALITY,
    block_size: int = ELA_BLOCK_SIZE,
    threshold: float = ELA_THRESHOLD,
) -> ForensicSignal:
    """Run ELA and find regions with anomalously high resave differences.

    Returns a complete ``ForensicSignal`` dict.
    """
    ela_img, max_diff, mean_diff = compute_ela(image, quality)
    ela_arr = np.asarray(ela_img, dtype=np.float32)
    h, w = ela_arr.shape

    hot_regions: list[ForensicRegion] = []
    block_diffs: list[float] = []

    for y in range(0, h - block_size + 1, block_size):
        for x in range(0, w - block_size + 1, block_size):
            block = ela_arr[y : y + block_size, x : x + block_size]
            block_mean = float(block.mean())
            # Convert normalized [0,255] back to raw pixel diff scale so
            # the threshold is in meaningful units (actual pixel-level diff).
            raw_block_mean = block_mean * max_diff / 255.0 if max_diff > 0 else 0.0
            block_diffs.append(raw_block_mean)
            if raw_block_mean > threshold:
                hot_regions.append(
                    ForensicRegion(
                        page=1,
                        bbox=[
                            round(x / w, 4),
                            round(y / h, 4),
                            round(min((x + block_size) / w, 1.0), 4),
                            round(min((y + block_size) / h, 1.0), 4),
                        ],
                        note=f"ELA block diff={raw_block_mean:.1f}",
                    )
                )

    # Merge nearby hot regions into clusters
    merged = _merge_nearby_regions(hot_regions, merge_distance=0.02)

    n_hot = len(hot_regions)
    fired = n_hot >= ELA_MIN_BLOCKS

    # Score: 0–100 based on how many blocks are hot relative to total blocks
    total_blocks = max(len(block_diffs), 1)
    hot_ratio = n_hot / total_blocks
    score = min(100.0, round(hot_ratio * 500, 1))  # 20% hot → score 100

    # Confidence: higher when we have enough data
    confidence = min(1.0, round(total_blocks / 100, 2)) if fired else 0.3

    detail = (
        f"ELA at Q{quality}: {n_hot}/{total_blocks} blocks exceed threshold "
        f"(mean diff={mean_diff:.1f}, max diff={max_diff:.1f})."
    )
    if not fired:
        detail = f"No significant ELA anomalies (mean diff={mean_diff:.1f})."

    return ForensicSignal(
        id="ela_hotspot",
        label="Error-level analysis hotspot",
        score=score,
        confidence=confidence,
        passed=not fired,
        pages=[1],
        regions=merged[:20],  # cap for UI sanity
        detail=detail,
    )


# ---------------------------------------------------------------------------
# §2  Noise Inconsistency
# ---------------------------------------------------------------------------


def detect_noise_inconsistency(
    image: Image.Image,
    block_size: int = NOISE_BLOCK_SIZE,
) -> ForensicSignal:
    """Compute per-block local noise variance and flag outliers.

    Spliced or edited regions tend to have a different noise signature than
    the background.
    """
    gray = image.convert("L") if image.mode != "L" else image
    arr = np.asarray(gray, dtype=np.float32)
    h, w = arr.shape

    # High-pass filter to isolate noise
    blurred = np.asarray(gray.filter(ImageFilter.GaussianBlur(radius=2)), dtype=np.float32)
    noise = arr - blurred

    block_vars: list[tuple[float, int, int]] = []  # (variance, x, y)
    for y in range(0, h - block_size + 1, block_size):
        for x in range(0, w - block_size + 1, block_size):
            block = noise[y : y + block_size, x : x + block_size]
            block_vars.append((float(np.var(block)), x, y))

    if len(block_vars) < 4:
        return ForensicSignal(
            id="noise_inconsistency",
            label="Noise inconsistency",
            score=0.0,
            confidence=0.1,
            passed=True,
            pages=[1],
            regions=[],
            detail="Image too small for meaningful noise analysis.",
        )

    variances = np.array([v[0] for v in block_vars])
    mean_var = float(variances.mean())
    std_var = float(variances.std())

    anomalies: list[ForensicRegion] = []
    if std_var > 1e-6:
        for var, x, y in block_vars:
            zscore = abs(var - mean_var) / std_var
            if zscore > NOISE_ZSCORE_THRESH:
                anomalies.append(
                    ForensicRegion(
                        page=1,
                        bbox=[
                            round(x / w, 4),
                            round(y / h, 4),
                            round(min((x + block_size) / w, 1.0), 4),
                            round(min((y + block_size) / h, 1.0), 4),
                        ],
                        note=f"Noise variance z-score={zscore:.1f}",
                    )
                )

    merged = _merge_nearby_regions(anomalies, merge_distance=0.02)
    n_anomalies = len(anomalies)
    total_blocks = len(block_vars)
    anomaly_ratio = n_anomalies / total_blocks
    fired = anomaly_ratio > 0.08  # >8% of blocks are anomalous

    score = min(100.0, round(anomaly_ratio * 400, 1))  # 25% anomalous → 100
    confidence = min(1.0, round(total_blocks / 200, 2))

    if fired:
        detail = (
            f"{n_anomalies}/{total_blocks} blocks show noise inconsistency "
            f"(σ of variances={std_var:.2f})."
        )
    else:
        detail = f"Noise variance is consistent across blocks (σ={std_var:.2f})."

    return ForensicSignal(
        id="noise_inconsistency",
        label="Noise inconsistency",
        score=score,
        confidence=confidence,
        passed=not fired,
        pages=[1],
        regions=merged[:20],
        detail=detail,
    )


# ---------------------------------------------------------------------------
# §3  Double JPEG Compression Detection
# ---------------------------------------------------------------------------


def detect_double_compression(image: Image.Image) -> ForensicSignal:
    """Detect double JPEG compression by analyzing DCT coefficient periodicity.

    Double-compressed JPEGs show characteristic periodic peaks in the
    histogram of DCT coefficients. We approximate this by analyzing the
    frequency content of the pixel-value histogram.
    """
    gray = image.convert("L") if image.mode != "L" else image
    arr = np.asarray(gray, dtype=np.float32)

    # Compute pixel-value histogram (proxy for DCT coefficient distribution)
    hist, _ = np.histogram(arr.ravel(), bins=DCT_HIST_BINS, range=(0, 256))
    hist = hist.astype(np.float64)

    # Remove DC component and normalize
    hist_mean = hist.mean()
    if hist_mean < 1e-6:
        return _clean_double_compression_signal()

    centered = hist - hist_mean

    # FFT of the histogram — periodic peaks show up as high-frequency spikes
    spectrum = np.abs(np.fft.rfft(centered))
    # Skip DC (index 0) and the first few low-frequency bins
    if len(spectrum) < 10:
        return _clean_double_compression_signal()

    high_freq = spectrum[5:]
    peak = float(high_freq.max())
    avg = float(high_freq.mean())

    if avg < 1e-6:
        return _clean_double_compression_signal()

    periodicity = peak / avg

    fired = periodicity > (1.0 + DCT_PERIOD_THRESH * 10)  # significant periodicity
    score = min(100.0, round(max(0, (periodicity - 1.0)) * 20, 1))
    confidence = min(1.0, round(0.4 + score / 200, 2))

    if fired:
        detail = f"Histogram periodicity ratio={periodicity:.2f} suggests double JPEG compression."
    else:
        detail = f"No double-compression artifacts detected (periodicity={periodicity:.2f})."

    return ForensicSignal(
        id="double_compression",
        label="Double JPEG compression",
        score=score,
        confidence=confidence,
        passed=not fired,
        pages=[1],
        regions=[],
        detail=detail,
    )


def _clean_double_compression_signal() -> ForensicSignal:
    return ForensicSignal(
        id="double_compression",
        label="Double JPEG compression",
        score=0.0,
        confidence=0.2,
        passed=True,
        pages=[1],
        regions=[],
        detail="No double-compression artifacts detected.",
    )


# ---------------------------------------------------------------------------
# §4  Copy-Move Detection
# ---------------------------------------------------------------------------


def detect_copy_move(image: Image.Image) -> ForensicSignal:
    """Detect duplicated (copy-pasted) regions within a single image.

    Uses a grid-based perceptual hash comparison: divide the image into blocks,
    hash each block, and flag blocks that share near-identical hashes at
    different locations.
    """
    gray = image.convert("L") if image.mode != "L" else image
    arr = np.asarray(gray, dtype=np.float32)
    h, w = arr.shape
    bs = COPY_MOVE_BLOCK

    if h < bs * 3 or w < bs * 3:
        return ForensicSignal(
            id="copy_move",
            label="Copy-move detection",
            score=0.0,
            confidence=0.1,
            passed=True,
            pages=[1],
            regions=[],
            detail="Image too small for copy-move analysis.",
        )

    # Extract block descriptors (mean + std + edge density + range)
    blocks: list[tuple[int, int, tuple[float, ...]]] = []
    for y in range(0, h - bs + 1, bs):
        for x in range(0, w - bs + 1, bs):
            block = arr[y : y + bs, x : x + bs]
            mean_val = float(block.mean())
            std_val = float(block.std())
            min_val = float(block.min())
            max_val = float(block.max())
            # Simple edge energy via Sobel-like horizontal diff
            dx = float(np.abs(np.diff(block, axis=1)).mean())
            dy = float(np.abs(np.diff(block, axis=0)).mean())
            # Quantize with 1 decimal place to reduce false matches
            # while still catching genuine copy-move duplicates.
            descriptor = (
                round(mean_val, 1),
                round(std_val, 1),
                round(dx, 1),
                round(dy, 1),
                round(min_val, 0),
                round(max_val, 0),
            )
            blocks.append((x, y, descriptor))

    # Find matching descriptors at different locations
    from collections import defaultdict

    desc_map: dict[tuple[float, ...], list[tuple[int, int]]] = defaultdict(list)
    for x, y, desc in blocks:
        desc_map[desc].append((x, y))

    matched_regions: list[ForensicRegion] = []
    for desc, positions in desc_map.items():
        if len(positions) < 2:
            continue
        # Skip near-uniform blocks (likely background / common texture)
        if desc[1] < 8.0:  # low std → uniform
            continue
        # Skip descriptors matching too many blocks — this indicates a
        # common texture pattern (e.g. noise, gradient) rather than a
        # genuine copy-move forgery which involves a small pasted region.
        if len(positions) > 20:
            continue
        # Only flag if blocks are far enough apart
        for i, (x1, y1) in enumerate(positions):
            for x2, y2 in positions[i + 1 :]:
                dist = math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
                if dist > bs * 3:  # not adjacent
                    matched_regions.append(
                        ForensicRegion(
                            page=1,
                            bbox=[
                                round(x1 / w, 4),
                                round(y1 / h, 4),
                                round(min((x1 + bs) / w, 1.0), 4),
                                round(min((y1 + bs) / h, 1.0), 4),
                            ],
                            note="Potential copy-move source",
                        )
                    )
                    matched_regions.append(
                        ForensicRegion(
                            page=1,
                            bbox=[
                                round(x2 / w, 4),
                                round(y2 / h, 4),
                                round(min((x2 + bs) / w, 1.0), 4),
                                round(min((y2 + bs) / h, 1.0), 4),
                            ],
                            note="Potential copy-move target",
                        )
                    )

    n_matches = len(matched_regions) // 2  # pairs
    fired = n_matches >= COPY_MOVE_MIN_MATCHES

    total_blocks = len(blocks)
    match_ratio = n_matches / max(total_blocks, 1)
    score = min(100.0, round(match_ratio * 1000, 1))
    confidence = 0.5 if fired else 0.3

    merged = _merge_nearby_regions(matched_regions, merge_distance=0.03)

    if fired:
        detail = f"{n_matches} block pairs match at distant positions (potential copy-move)."
    else:
        detail = "No significant copy-move patterns detected."

    return ForensicSignal(
        id="copy_move",
        label="Copy-move detection",
        score=score,
        confidence=confidence,
        passed=not fired,
        pages=[1],
        regions=merged[:20],
        detail=detail,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _merge_nearby_regions(
    regions: list[ForensicRegion],
    merge_distance: float = 0.02,
) -> list[ForensicRegion]:
    """Merge overlapping or very-close regions into larger bounding boxes."""
    if not regions:
        return []

    # Sort by top-left corner
    sorted_regs = sorted(regions, key=lambda r: (r["bbox"][1], r["bbox"][0]))
    merged: list[ForensicRegion] = [sorted_regs[0].copy()]  # type: ignore[misc]

    for reg in sorted_regs[1:]:
        last = merged[-1]
        # Check if close enough to merge
        if (
            reg["bbox"][0] <= last["bbox"][2] + merge_distance
            and reg["bbox"][1] <= last["bbox"][3] + merge_distance
        ):
            # Expand the last region
            merged[-1] = ForensicRegion(
                page=last["page"],
                bbox=[
                    min(last["bbox"][0], reg["bbox"][0]),
                    min(last["bbox"][1], reg["bbox"][1]),
                    max(last["bbox"][2], reg["bbox"][2]),
                    max(last["bbox"][3], reg["bbox"][3]),
                ],
                note=last.get("note"),
            )
        else:
            merged.append(reg.copy())  # type: ignore[misc]

    return merged
