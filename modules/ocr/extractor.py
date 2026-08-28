"""Text & field extraction.

Owner: OCR developer.
Produces: ``Extraction`` (contract §2).

Pipeline, per document:

    raw bytes -> rasterize() -> [PIL pages]
              -> preprocess() each page (orientation, grayscale, contrast, resize)
              -> engine.run_ocr() each page (Tesseract, if installed)
              -> fields.extract_fields() each page
              -> merge into one contract-shaped ``Extraction``

Never fabricates output. If Tesseract is missing, or a page can't be decoded,
``extract()`` still returns a *valid* ``Extraction`` -- empty text, empty
fields, ``text_confidence = 0.0`` -- with a warning explaining why, per this
module's README. Only a truly unexpected error (a bug, not a missing tool or
bad input) is allowed to raise; the backend converts that to a ``ModuleError``.
"""

from __future__ import annotations

from modules.contract import Document, Extraction, ExtractionField, ExtractionPageInfo

from .engine import is_available, run_ocr, tesseract_status
from .fields import extract_fields
from .preprocess import preprocess
from .rasterize import RasterizeError, rasterize

ENGINE = "tesseract"
ENGINE_VERSION_UNAVAILABLE = "0.0.0"
DEFAULT_LANG = "eng"


def _empty_extraction(warnings: list[str], engine_version: str = ENGINE_VERSION_UNAVAILABLE) -> Extraction:
    return Extraction(
        engine=ENGINE,
        engine_version=engine_version,
        language=None,
        full_text="",
        text_confidence=0.0,
        fields=[],
        tables=[],
        warnings=warnings,
        pages=[],
    )


def _merge_fields(all_fields: list[ExtractionField]) -> list[ExtractionField]:
    """Union fields across pages, keeping the highest-confidence duplicate.

    A duplicate is the same ``key`` + ``value_normalized`` (or same raw
    ``value`` if normalization is unavailable) found on more than one page --
    common for a document number or a name that appears on every page.
    """
    best: dict[tuple[str, str | None], ExtractionField] = {}
    for f in all_fields:
        dedupe_key = (f["key"], f["value_normalized"] or f["value"])
        existing = best.get(dedupe_key)
        if existing is None or f["confidence"] > existing["confidence"]:
            best[dedupe_key] = f
    return list(best.values())


def extract(document: Document, data: bytes) -> Extraction:
    """Extract text and structured fields from one uploaded document.

    Parameters
    ----------
    document:
        The normalized ``Document`` (contract §1) from the backend. Used for
        its ``media_type`` / ``filename`` (to classify PDF vs. image) and to
        tag warnings.
    data:
        The document's raw file bytes, exactly as uploaded.

    Returns
    -------
    Extraction
        Contract §2. Always contract-valid, even when OCR could not run.
    """
    warnings: list[str] = []

    try:
        page_images, source_kind = rasterize(
            data, media_type=document.get("media_type"), filename=document.get("filename")
        )
    except RasterizeError as exc:
        return _empty_extraction([f"could not decode document {document.get('filename')!r}: {exc}"])

    status = tesseract_status()
    engine_version = str(status["version"]) if status["available"] else ENGINE_VERSION_UNAVAILABLE
    if not is_available():
        warnings.append(f"Tesseract OCR is not available: {status['reason']}")

    page_infos: list[ExtractionPageInfo] = []
    page_fields: list[ExtractionField] = []
    page_texts: list[str] = []
    conf_weighted_sum = 0.0
    conf_weight_total = 0

    for page_number, raw_image in enumerate(page_images, start=1):
        pre = preprocess(raw_image)
        result = run_ocr(pre.image, lang=DEFAULT_LANG)

        char_count = len(result.text)
        page_infos.append(
            ExtractionPageInfo(
                page_number=page_number,
                source=source_kind,
                width=pre.width,
                height=pre.height,
                rotation_applied=pre.rotation_applied,
                text_confidence=result.mean_conf,
                char_count=char_count,
            )
        )
        if result.text.strip():
            page_texts.append(result.text.strip())
        if result.ran and result.words:
            conf_weighted_sum += result.mean_conf * len(result.words)
            conf_weight_total += len(result.words)

        field_result = extract_fields(
            result.text,
            result.words,
            page=page_number,
            page_width=pre.width,
            page_height=pre.height,
            ocr_confidence=result.mean_conf,
        )
        page_fields.extend(field_result.fields)
        warnings.extend(field_result.warnings)

    full_text = "\n\n".join(page_texts)
    text_confidence = round(conf_weighted_sum / conf_weight_total, 4) if conf_weight_total else 0.0
    merged_fields = _merge_fields(page_fields)

    return Extraction(
        engine=ENGINE,
        engine_version=engine_version,
        language=DEFAULT_LANG if any(pi["char_count"] for pi in page_infos) else None,
        full_text=full_text,
        text_confidence=text_confidence,
        fields=merged_fields,
        tables=[],
        warnings=warnings,
        pages=page_infos,
    )
