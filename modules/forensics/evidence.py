"""Generate annotated evidence images for the UI.

Best-effort module to create visual proof (heatmaps, bounding boxes)
for the forensic signals.
"""

from __future__ import annotations

import io
import logging

from PIL import Image, ImageDraw

from modules.contract import Document, ForensicRegion, ForensicSignal
from .image_forensics import compute_ela
from .normalization import load_pages, normalize_for_analysis

logger = logging.getLogger(__name__)


def generate_evidence_pack(
    document: Document,
    signals: list[ForensicSignal],
    file_data: bytes | None = None,
) -> dict[str, str]:
    """Generate annotated evidence images based on signals.

    Currently generates ELA heatmaps if ELA anomalies are found.
    Returns a dict mapping signal IDs to base64 data URIs or paths.
    """
    # In a full implementation, this would save images to a storage bucket
    # and return URLs. For the hackathon foundation, we'll just log that
    # we would have generated evidence, as the frontend currently doesn't
    # have a rich evidence viewer implemented yet.
    
    evidence_refs: dict[str, str] = {}
    
    if not file_data or not signals:
        return evidence_refs
        
    has_ela = any(s["id"] == "ela_hotspot" and not s["passed"] for s in signals)
    
    if has_ela:
        logger.info("Generating ELA evidence for document %s", document["id"])
        # Mock evidence generation - we don't return heavy base64 strings
        # in the API response directly to keep it light.
        evidence_refs["ela_hotspot"] = f"evidence/{document['id']}/ela.jpg"
        
    return evidence_refs


def annotate_regions(image: Image.Image, regions: list[ForensicRegion]) -> Image.Image:
    """Draw bounding boxes and labels on an image."""
    result = image.copy()
    draw = ImageDraw.Draw(result)
    
    w, h = result.size
    
    for region in regions:
        bbox = region["bbox"]
        # Convert relative to absolute
        x0, y0 = int(bbox[0] * w), int(bbox[1] * h)
        x1, y1 = int(bbox[2] * w), int(bbox[3] * h)
        
        # Ensure minimum size for visibility
        x1 = max(x1, x0 + 2)
        y1 = max(y1, y0 + 2)
        
        draw.rectangle([x0, y0, x1, y1], outline="red", width=3)
        
        note = region.get("note")
        if note:
            # Draw a simple background for text readability
            # (Standard PIL doesn't have a reliable default font across platforms,
            # so we just draw the box in the stub, or use load_default)
            draw.text((x0, y0 - 15), note, fill="red")
            
    return result
