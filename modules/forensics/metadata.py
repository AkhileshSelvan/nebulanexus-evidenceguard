"""File-history / metadata plausibility.

Owner: Forensics developer (may be spun out into its own module later —
that's why it has a separate entry point and contract section).
Produces: ``Metadata`` (contract §4).

Real PDF/EXIF/PNG metadata extraction with plausibility signals.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from modules.contract import Document, Metadata, MetadataDerived, MetadataSignal

logger = logging.getLogger(__name__)

ENGINE = "evidenceguard-metadata"
ENGINE_VERSION = "0.2.0"

# Image editors that raise a flag when found as Producer/Creator
IMAGE_EDITOR_PATTERNS: list[str] = [
    r"photoshop",
    r"gimp",
    r"paint\.net",
    r"pixlr",
    r"canva",
    r"affinity\s*photo",
    r"inkscape",
    r"illustrator",
    r"corel",
    r"krita",
    r"photo\s*editor",
    r"image\s*editor",
    r"snapseed",
]

# Gap (in seconds) between creation and modification that's considered suspicious
SUSPICIOUS_EDIT_GAP_SECONDS = 3600  # 1 hour

# Absent metadata is weak evidence: scanners, scan apps and "print to PDF" all
# routinely produce files with a thin or empty info dictionary. These caps keep
# the finding visible to a reviewer while stopping it from carrying a decision.
# (Was 40.0 / 15.0-per-field; measured firing on 6 of 9 genuine scanned PDFs.)
MISSING_METADATA_ABSENT_SCORE = 12.0   # no metadata at all
MISSING_METADATA_PARTIAL_CAP = 10.0    # some expected fields absent


def extract_metadata(
    document: Document,
    file_path: str | None = None,
    *,
    file_data: bytes | None = None,
) -> Metadata:
    """Extract and sanity-check a document's embedded metadata.

    Parameters
    ----------
    document:
        Normalized ``Document`` (contract §1).
    file_path:
        Absolute path to the *original* uploaded bytes.
    file_data:
        Raw file bytes (alternative to *file_path*).

    Returns
    -------
    Metadata
        Contract §4. Returns real metadata with plausibility signals.
        Never raises — returns empty metadata on error.
    """
    media_type = document.get("media_type", "application/octet-stream")
    container = _container_for_media_type(media_type)

    # Load file data from path if not provided directly
    data = file_data
    if data is None and file_path:
        try:
            with open(file_path, "rb") as f:
                data = f.read()
        except OSError as exc:
            logger.warning("Could not read file for metadata: %s", exc)

    # Extract raw metadata based on container type
    raw: dict[str, Any] = {}
    if data:
        try:
            if container == "pdf":
                raw = _extract_pdf_metadata(data)
            elif container == "jpeg":
                raw = _extract_exif_metadata(data)
            elif container == "png":
                raw = _extract_png_metadata(data)
        except Exception as exc:
            logger.warning("Metadata extraction failed: %s", exc)

    # Derive normalized fields
    derived = _derive_fields(raw, container)

    # Run plausibility signals
    signals = _run_plausibility_signals(raw, derived, container, document)

    # Roll up score
    score = _rollup_score(signals)
    summary = _build_summary(signals, score, raw)

    return Metadata(
        engine=ENGINE,
        engine_version=ENGINE_VERSION,
        container=container,
        raw=raw,
        derived=derived,
        signals=signals,
        score=score,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Container-specific extraction
# ---------------------------------------------------------------------------


def _extract_pdf_metadata(data: bytes) -> dict[str, Any]:
    """Extract metadata from a PDF using pikepdf."""
    raw: dict[str, Any] = {}

    try:
        import pikepdf
    except ImportError:
        logger.warning("pikepdf not available — falling back to basic extraction")
        return _extract_pdf_metadata_basic(data)

    try:
        import io as _io
        pdf = pikepdf.open(_io.BytesIO(data))
    except Exception as exc:
        logger.warning("pikepdf could not open PDF: %s", exc)
        return _extract_pdf_metadata_basic(data)

    try:
        # Info dict (traditional metadata)
        info = pdf.docinfo
        if info:
            for key in info.keys():
                try:
                    val = str(info[key])
                    # Clean up pikepdf string representation
                    if val.startswith("'") and val.endswith("'"):
                        val = val[1:-1]
                    raw[key.lstrip("/")] = val
                except Exception:
                    pass

        # XMP metadata (if present)
        try:
            if pdf.open_metadata() is not None:
                with pdf.open_metadata() as xmp:
                    for key in [
                        "dc:creator", "dc:title", "dc:description",
                        "xmp:CreateDate", "xmp:ModifyDate", "xmp:CreatorTool",
                        "pdf:Producer",
                    ]:
                        try:
                            val = xmp.get(key)
                            if val:
                                raw[f"XMP:{key}"] = str(val)
                        except Exception:
                            pass
        except Exception:
            pass  # XMP might not exist
    finally:
        pdf.close()

    return raw


def _extract_pdf_metadata_basic(data: bytes) -> dict[str, Any]:
    """Fallback PDF metadata extraction using pymupdf."""
    raw: dict[str, Any] = {}
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf  # type: ignore[no-redef]
        except ImportError:
            return raw

    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
        meta = doc.metadata
        if meta:
            for key, val in meta.items():
                if val:
                    raw[key] = val
        doc.close()
    except Exception:
        pass

    return raw


def _extract_exif_metadata(data: bytes) -> dict[str, Any]:
    """Extract EXIF metadata from a JPEG using piexif."""
    raw: dict[str, Any] = {}

    try:
        import piexif
    except ImportError:
        logger.warning("piexif not available — cannot extract EXIF")
        return raw

    try:
        exif_dict = piexif.load(data)
    except Exception as exc:
        logger.warning("EXIF extraction failed: %s", exc)
        return raw

    # Map EXIF IFD tags to human-readable keys
    ifd_names = {
        "0th": piexif.ImageIFD,
        "Exif": piexif.ExifIFD,
        "GPS": piexif.GPSIFD,
        "1st": piexif.ImageIFD,
    }

    for ifd_key, ifd_data in exif_dict.items():
        if ifd_key == "thumbnail" or not isinstance(ifd_data, dict):
            continue
        for tag_id, value in ifd_data.items():
            try:
                tag_name = piexif.TAGS.get(ifd_key, {}).get(tag_id, {}).get("name", f"Tag_{tag_id}")
                # Decode bytes to string if possible
                if isinstance(value, bytes):
                    try:
                        value = value.decode("utf-8", errors="replace").rstrip("\x00")
                    except Exception:
                        value = value.hex()
                elif isinstance(value, tuple):
                    value = str(value)
                raw[f"EXIF:{tag_name}"] = str(value)
            except Exception:
                pass

    # Check for GPS data
    gps_data = exif_dict.get("GPS", {})
    if gps_data:
        raw["_has_gps"] = True
        for tag_id, value in gps_data.items():
            try:
                tag_name = piexif.TAGS.get("GPS", {}).get(tag_id, {}).get("name", f"GPS_{tag_id}")
                raw[f"GPS:{tag_name}"] = str(value)
            except Exception:
                pass

    return raw


def _extract_png_metadata(data: bytes) -> dict[str, Any]:
    """Extract metadata from PNG text chunks."""
    raw: dict[str, Any] = {}

    try:
        from PIL import Image
        import io

        img = Image.open(io.BytesIO(data))
        img.load()

        # PNG text chunks are stored in img.info
        for key, value in img.info.items():
            if isinstance(value, (str, bytes)):
                if isinstance(value, bytes):
                    try:
                        value = value.decode("utf-8", errors="replace")
                    except Exception:
                        value = value.hex()
                raw[f"PNG:{key}"] = str(value)
    except Exception as exc:
        logger.warning("PNG metadata extraction failed: %s", exc)

    return raw


# ---------------------------------------------------------------------------
# Field derivation
# ---------------------------------------------------------------------------


def _derive_fields(raw: dict[str, Any], container: str) -> MetadataDerived:
    """Normalize raw metadata into the contract's derived fields."""
    created_at = _find_date(raw, [
        "CreationDate", "creation", "creationDate",
        "XMP:xmp:CreateDate", "EXIF:DateTimeOriginal",
        "EXIF:DateTimeDigitized",
    ])
    modified_at = _find_date(raw, [
        "ModDate", "modDate", "XMP:xmp:ModifyDate",
        "EXIF:DateTime",
    ])

    producer = _find_value(raw, [
        "Producer", "producer", "pdf:Producer", "XMP:pdf:Producer",
    ])
    creator_tool = _find_value(raw, [
        "Creator", "creator", "XMP:xmp:CreatorTool", "CreatorTool",
        "EXIF:Software",
    ])

    has_gps = bool(raw.get("_has_gps", False))

    # Build software edit chain
    software_edits: list[str] = []
    for val in [producer, creator_tool]:
        if val and val not in software_edits:
            software_edits.append(val)
    exif_software = raw.get("EXIF:Software")
    if exif_software and exif_software not in software_edits:
        software_edits.append(exif_software)

    return MetadataDerived(
        created_at=created_at,
        modified_at=modified_at,
        producer=producer,
        creator_tool=creator_tool,
        has_gps=has_gps,
        software_edits=software_edits,
    )


def _find_date(raw: dict[str, Any], keys: list[str]) -> str | None:
    """Find the first date value in raw metadata and normalize to ISO 8601."""
    for key in keys:
        val = raw.get(key)
        if val:
            parsed = _parse_date(str(val))
            if parsed:
                return parsed
    return None


def _find_value(raw: dict[str, Any], keys: list[str]) -> str | None:
    """Find the first non-empty value for any of the given keys."""
    for key in keys:
        val = raw.get(key)
        if val:
            return str(val).strip()
    return None


def _parse_date(s: str) -> str | None:
    """Best-effort date parsing into ISO 8601 format."""
    s = s.strip()

    # PDF date format: D:YYYYMMDDHHmmSS+HH'mm'
    pdf_match = re.match(
        r"D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})", s
    )
    if pdf_match:
        g = pdf_match.groups()
        try:
            dt = datetime(int(g[0]), int(g[1]), int(g[2]),
                          int(g[3]), int(g[4]), int(g[5]),
                          tzinfo=timezone.utc)
            return dt.isoformat()
        except (ValueError, OverflowError):
            pass

    # ISO 8601 variants
    for fmt in [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y:%m:%d %H:%M:%S",  # EXIF format
        "%Y-%m-%d",
    ]:
        try:
            dt = datetime.strptime(s[:len(s)], fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except (ValueError, OverflowError):
            continue

    return None


# ---------------------------------------------------------------------------
# Plausibility signals
# ---------------------------------------------------------------------------


def _run_plausibility_signals(
    raw: dict[str, Any],
    derived: MetadataDerived,
    container: str,
    document: Document,
) -> list[MetadataSignal]:
    """Run all metadata plausibility checks."""
    signals: list[MetadataSignal] = []

    signals.append(_check_modified_after_creation(derived))
    signals.append(_check_future_timestamp(derived))
    signals.append(_check_editor_is_image_tool(derived))
    signals.append(_check_missing_expected_metadata(raw, container, document))
    signals.append(_check_timezone_mismatch(raw, derived))
    signals.append(_check_producer_mismatch(derived, document))

    return signals


def _check_modified_after_creation(derived: MetadataDerived) -> MetadataSignal:
    """Check if modified date is suspiciously far from creation date."""
    created = derived.get("created_at")
    modified = derived.get("modified_at")

    if not created or not modified:
        return MetadataSignal(
            id="modified_after_creation",
            label="Modified after creation",
            score=0.0,
            confidence=0.1,
            passed=True,
            detail="Cannot check — creation or modification date missing.",
        )

    try:
        dt_created = datetime.fromisoformat(created)
        dt_modified = datetime.fromisoformat(modified)
        gap = (dt_modified - dt_created).total_seconds()
    except (ValueError, OverflowError):
        return MetadataSignal(
            id="modified_after_creation",
            label="Modified after creation",
            score=0.0,
            confidence=0.1,
            passed=True,
            detail="Could not parse date values.",
        )

    if gap < 0:
        # Modified before created — very suspicious
        return MetadataSignal(
            id="modified_after_creation",
            label="Modified before creation",
            score=80.0,
            confidence=0.8,
            passed=False,
            detail=f"Modified date is {abs(gap):.0f}s BEFORE creation date — possible clock/metadata tampering.",
        )

    if gap > SUSPICIOUS_EDIT_GAP_SECONDS:
        hours = gap / 3600
        score = min(70.0, round(hours * 2, 1))
        return MetadataSignal(
            id="modified_after_creation",
            label="Modified significantly after creation",
            score=score,
            confidence=0.7,
            passed=False,
            detail=f"Modified {hours:.1f}h after creation — document was edited post-creation.",
        )

    # Normal gap
    return MetadataSignal(
        id="modified_after_creation",
        label="Modified shortly after creation",
        score=0.0,
        confidence=0.6,
        passed=True,
        detail=f"{gap:.0f}s gap between creation and modification — within normal range.",
    )


def _check_future_timestamp(derived: MetadataDerived) -> MetadataSignal:
    """Check if any metadata dates are in the future."""
    now = datetime.now(timezone.utc)
    future_dates: list[str] = []

    for label, key in [("Created", "created_at"), ("Modified", "modified_at")]:
        val = derived.get(key)
        if val:
            try:
                dt = datetime.fromisoformat(val)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt > now:
                    future_dates.append(f"{label}: {val}")
            except (ValueError, OverflowError):
                pass

    if future_dates:
        return MetadataSignal(
            id="future_timestamp",
            label="Future timestamp",
            score=75.0,
            confidence=0.9,
            passed=False,
            detail=f"Date(s) in the future: {'; '.join(future_dates)}.",
        )

    return MetadataSignal(
        id="future_timestamp",
        label="Future timestamp",
        score=0.0,
        confidence=0.5,
        passed=True,
        detail="No future timestamps found.",
    )


def _check_editor_is_image_tool(derived: MetadataDerived) -> MetadataSignal:
    """Check if the Producer/Creator is a known image editing tool."""
    tools_to_check = []
    if derived.get("producer"):
        tools_to_check.append(("Producer", derived["producer"]))
    if derived.get("creator_tool"):
        tools_to_check.append(("Creator", derived["creator_tool"]))
    for sw in derived.get("software_edits", []):
        tools_to_check.append(("Software", sw))

    if not tools_to_check:
        return MetadataSignal(
            id="editor_is_image_tool",
            label="Image editor detected",
            score=0.0,
            confidence=0.1,
            passed=True,
            detail="No producer/creator metadata to check.",
        )

    matches: list[str] = []
    for label, tool in tools_to_check:
        tool_lower = tool.lower()
        for pattern in IMAGE_EDITOR_PATTERNS:
            if re.search(pattern, tool_lower):
                matches.append(f"{label}: {tool}")
                break

    if matches:
        return MetadataSignal(
            id="editor_is_image_tool",
            label="Image editor detected in tool chain",
            score=60.0,
            confidence=0.85,
            passed=False,
            detail=f"Image editor(s) found: {'; '.join(matches)}. "
                   f"Documents from official sources rarely pass through image editors.",
        )

    return MetadataSignal(
        id="editor_is_image_tool",
        label="Image editor check",
        score=0.0,
        confidence=0.5,
        passed=True,
        detail=f"No image editors detected in tool chain: "
               f"{', '.join(t for _, t in tools_to_check)}.",
    )


def _check_missing_expected_metadata(
    raw: dict[str, Any],
    container: str,
    document: Document,
) -> MetadataSignal:
    """Check if metadata is missing that we'd expect for this document type.

    Absence of metadata is weak evidence at best. Scanners, phone scan apps and
    "print to PDF" routinely emit files with little or no info dictionary, and
    many tools strip EXIF on export. On a real bundle of legitimate scanned
    credentials this fired on 6 of 9 documents (see the calibration audit), so
    it is reported for the reviewer but kept below the level where it can move a
    decision on its own.
    """
    if not raw:
        return MetadataSignal(
            id="missing_expected_metadata",
            label="Missing expected metadata",
            score=MISSING_METADATA_ABSENT_SCORE,
            confidence=0.25,
            passed=False,
            detail=(
                f"No metadata at all for a {container} file. Common for scanner "
                "and 'print to PDF' output, so informational rather than "
                "evidence of manipulation."
            ),
        )

    missing: list[str] = []

    if container == "pdf":
        # Use substring matching: "creation" matches "CreationDate", etc.
        expected_substrings = ["producer", "creation", "creator", "mod"]
        for expected in expected_substrings:
            found = any(expected in rk.lower() for rk in raw)
            if not found:
                missing.append(expected)

    elif container == "jpeg":
        if not any("EXIF:" in k for k in raw):
            missing.append("EXIF data")

    if missing:
        return MetadataSignal(
            id="missing_expected_metadata",
            label="Missing expected metadata",
            score=min(MISSING_METADATA_PARTIAL_CAP, len(missing) * 3.0),
            confidence=0.25,
            passed=False,
            detail=(
                f"Expected metadata fields missing: {', '.join(missing)}. "
                "Routine for scanned/exported documents — informational."
            ),
        )

    return MetadataSignal(
        id="missing_expected_metadata",
        label="Expected metadata present",
        score=0.0,
        confidence=0.5,
        passed=True,
        detail="Expected metadata fields are present.",
    )


def _check_timezone_mismatch(raw: dict[str, Any], derived: MetadataDerived) -> MetadataSignal:
    """Check if creation and modification dates use different timezones."""
    created = derived.get("created_at")
    modified = derived.get("modified_at")

    if not created or not modified:
        return MetadataSignal(
            id="timezone_mismatch",
            label="Timezone mismatch",
            score=0.0,
            confidence=0.1,
            passed=True,
            detail="Cannot check — dates missing.",
        )

    try:
        dt_created = datetime.fromisoformat(created)
        dt_modified = datetime.fromisoformat(modified)

        tz1 = dt_created.tzinfo
        tz2 = dt_modified.tzinfo

        if tz1 and tz2:
            offset1 = dt_created.utcoffset()
            offset2 = dt_modified.utcoffset()
            if offset1 != offset2:
                return MetadataSignal(
                    id="timezone_mismatch",
                    label="Timezone mismatch between dates",
                    score=35.0,
                    confidence=0.6,
                    passed=False,
                    detail=f"Created in {offset1}, modified in {offset2} — different timezones.",
                )
    except (ValueError, OverflowError):
        pass

    return MetadataSignal(
        id="timezone_mismatch",
        label="Timezone consistency",
        score=0.0,
        confidence=0.4,
        passed=True,
        detail="Timezone information is consistent (or not available to compare).",
    )


def _check_producer_mismatch(derived: MetadataDerived, document: Document) -> MetadataSignal:
    """Check if the producer software is unusual for the declared document type."""
    producer = derived.get("producer") or ""
    creator = derived.get("creator_tool") or ""
    declared_type = document.get("declared_type") or ""

    if not producer and not creator:
        return MetadataSignal(
            id="producer_mismatch_for_issuer",
            label="Producer/issuer match",
            score=0.0,
            confidence=0.1,
            passed=True,
            detail="No producer information to check.",
        )

    # Payslips/bank statements from image editors are suspicious
    official_types = {"payslip", "bank_statement", "id_card", "passport", "tax_return"}
    tool_chain = f"{producer} {creator}".lower()

    if declared_type.lower() in official_types:
        for pattern in IMAGE_EDITOR_PATTERNS:
            if re.search(pattern, tool_chain):
                return MetadataSignal(
                    id="producer_mismatch_for_issuer",
                    label="Producer unexpected for document type",
                    score=65.0,
                    confidence=0.7,
                    passed=False,
                    detail=f"A '{declared_type}' produced by an image editor ({producer or creator}) "
                           f"is unusual — official documents come from payroll/banking systems.",
                )

    return MetadataSignal(
        id="producer_mismatch_for_issuer",
        label="Producer/issuer match",
        score=0.0,
        confidence=0.3,
        passed=True,
        detail=f"Producer ({producer or 'unknown'}) is not flagged for type '{declared_type or 'unspecified'}'.",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _container_for_media_type(media_type: str) -> str:
    mapping = {
        "application/pdf": "pdf",
        "image/jpeg": "jpeg",
        "image/jpg": "jpeg",
        "image/png": "png",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    }
    return mapping.get(media_type, "unknown")


def _rollup_score(signals: list[MetadataSignal]) -> float:
    """Roll up signal scores into a section score."""
    if not signals:
        return 0.0
    # Weighted average, but signals with score 0 still count
    failed = [s for s in signals if not s["passed"]]
    if not failed:
        return 0.0
    return round(min(100.0, max(s["score"] for s in failed)), 1)


def _build_summary(signals: list[MetadataSignal], score: float, raw: dict) -> str:
    """Build a human-readable metadata summary."""
    failed = [s for s in signals if not s["passed"]]

    if not raw:
        return "No metadata could be extracted."

    if not failed:
        return "Metadata is internally consistent."

    labels = [s["label"] for s in failed[:3]]
    label_str = ", ".join(labels)
    n = len(failed)
    if n > 3:
        label_str += f", and {n - 3} more"

    return f"{n} metadata concern(s): {label_str}."
