"""Fixtures for modules/consistency tests.

Builds real ``Document`` / ``Extraction`` / ``ExtractionField`` dicts by hand
(the exact contract shapes ``modules/ocr`` produces) so tests exercise
``check_consistency`` against genuine contract-shaped input, without needing
an actual OCR run -- consistency's job starts after extraction, not before.
"""

from __future__ import annotations

from modules.contract import Document, Extraction, ExtractionField


def make_document(doc_id: str, filename: str = "doc.pdf") -> Document:
    return Document(
        id=doc_id,
        bundle_id="bnd_test0001",
        filename=filename,
        media_type="application/pdf",
        byte_size=1024,
        sha256="0" * 64,
        page_count=1,
        declared_type=None,
        detected_type=None,
        pages=[],
        received_at="2026-08-28T00:00:00Z",
    )


def make_field(
    key: str,
    value: str,
    *,
    normalized: str | None = None,
    data_type: str = "string",
    confidence: float = 0.9,
) -> ExtractionField:
    return ExtractionField(
        key=key,
        value=value,
        value_normalized=normalized if normalized is not None else value.strip().lower(),
        data_type=data_type,  # type: ignore[typeddict-item]
        confidence=confidence,
        page=1,
        bbox=None,
    )


def make_extraction(fields: list[ExtractionField]) -> Extraction:
    return Extraction(
        engine="tesseract",
        engine_version="5.3.4",
        language="eng",
        full_text="",
        text_confidence=0.9,
        fields=fields,
        tables=[],
        warnings=[],
        pages=[],
    )
