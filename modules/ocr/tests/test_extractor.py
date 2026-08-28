"""End-to-end tests for ``modules.ocr.extract`` -- the real pipeline, not a
mock: rasterize -> preprocess -> Tesseract -> field extraction.
"""

from __future__ import annotations

from modules.ocr import extract
from modules.ocr.rasterize import RasterizeError, rasterize

from .conftest import render_text_pdf, render_text_png


def test_extracts_real_text_from_a_png(make_document, ocr_font_or_skip):
    png_bytes = render_text_png(
        ["Certificate of Completion", "Document Number: AB123456"],
        ocr_font_or_skip,
    )
    doc = make_document("cert.png", "image/png", len(png_bytes))

    result = extract(doc, png_bytes)

    assert result["engine"] == "tesseract"
    assert "warnings" in result and isinstance(result["warnings"], list)
    assert len(result["pages"]) == 1
    assert result["pages"][0]["source"] == "image"
    # Real Tesseract output on rendered text is not pixel-perfect, but the
    # words themselves should come through.
    assert "Certificate" in result["full_text"]
    assert "AB123456" in result["full_text"] or any(
        f["key"] == "document_number" for f in result["fields"]
    )


def test_extracts_labelled_document_number_field(make_document, ocr_font_or_skip):
    png_bytes = render_text_png(
        ["Registration Number: REG998877", "Issued to: Jane Doe"],
        ocr_font_or_skip,
    )
    doc = make_document("reg.png", "image/png", len(png_bytes))

    result = extract(doc, png_bytes)

    doc_number_fields = [f for f in result["fields"] if f["key"] == "document_number"]
    assert doc_number_fields, f"expected a document_number field, got {result['fields']}"
    assert "REG998877" in doc_number_fields[0]["value"]
    assert 0.0 < doc_number_fields[0]["confidence"] <= 1.0


def test_multi_page_pdf_aggregates_across_pages(make_document, ocr_font_or_skip):
    pdf_bytes = render_text_pdf(
        [
            ["Page one of the report", "Reference: REF-000111"],
            ["Page two continues", "Reference: REF-000111"],  # same ref both pages
        ]
    )
    doc = make_document("report.pdf", "application/pdf", len(pdf_bytes))

    result = extract(doc, pdf_bytes)

    assert len(result["pages"]) == 2
    assert all(p["source"] == "pdf" for p in result["pages"])
    assert "Page one" in result["full_text"] and "Page two" in result["full_text"]
    # The repeated reference number should be merged, not duplicated.
    ref_fields = [f for f in result["fields"] if f["value_normalized"] == "ref000111"]
    assert len(ref_fields) <= 1


def test_undecodable_bytes_returns_valid_empty_extraction_not_a_raise(make_document):
    doc = make_document("mystery.png", "image/png", 4)

    result = extract(doc, b"\x00\x01\x02\x03")  # not a real PNG

    assert result["full_text"] == ""
    assert result["fields"] == []
    assert result["text_confidence"] == 0.0
    assert result["pages"] == []
    assert any("could not decode" in w for w in result["warnings"])


def test_unsupported_media_type_does_not_raise(make_document):
    doc = make_document("notes.txt", "text/plain", 11)

    result = extract(doc, b"hello world")

    assert result["fields"] == []
    assert result["pages"] == []
    assert result["warnings"]


def test_empty_bytes_does_not_raise(make_document):
    doc = make_document("empty.png", "image/png", 0)

    result = extract(doc, b"")

    assert result["full_text"] == ""
    assert result["pages"] == []


def test_rasterize_sniffs_bytes_when_media_type_is_unrecognized(ocr_font_or_skip):
    # An unrecognized/missing MIME type -- rasterize() falls back to sniffing
    # the actual bytes rather than guessing from the (wrong) extension.
    png_bytes = render_text_png(["mislabelled"], ocr_font_or_skip)
    pages, kind = rasterize(png_bytes, media_type="application/octet-stream", filename="not-a-pdf.dat")
    assert kind == "image"
    assert len(pages) == 1


def test_mismatched_media_type_still_decodes_via_content_sniffing(make_document, ocr_font_or_skip):
    # PNG bytes declared as PDF: PyMuPDF's own format detection is lenient
    # enough to still decode real image bytes even when told filetype="pdf",
    # so this succeeds rather than failing -- documenting that robustness.
    png_bytes = render_text_png(["mismatched type"], ocr_font_or_skip)
    doc = make_document("actually-a-png.pdf", "application/pdf", len(png_bytes))

    result = extract(doc, png_bytes)

    assert "mismatched" in result["full_text"].lower()


def test_rasterize_raises_on_garbage():
    try:
        rasterize(b"not a real file at all", media_type=None, filename="thing.bin")
        assert False, "expected RasterizeError"
    except RasterizeError:
        pass


def test_extraction_shape_matches_contract(make_document, ocr_font_or_skip):
    png_bytes = render_text_png(["Shape check"], ocr_font_or_skip)
    doc = make_document("shape.png", "image/png", len(png_bytes))

    result = extract(doc, png_bytes)

    for key in (
        "engine", "engine_version", "language", "full_text", "text_confidence",
        "fields", "tables", "warnings", "pages",
    ):
        assert key in result, f"Extraction missing contract key {key!r}"
    assert isinstance(result["fields"], list)
    assert isinstance(result["tables"], list)
    for field in result["fields"]:
        for fkey in ("key", "value", "value_normalized", "data_type", "confidence", "page", "bbox"):
            assert fkey in field, f"ExtractionField missing contract key {fkey!r}"
        assert 0.0 <= field["confidence"] <= 1.0
    for page in result["pages"]:
        for pkey in (
            "page_number", "source", "width", "height",
            "rotation_applied", "text_confidence", "char_count",
        ):
            assert pkey in page, f"ExtractionPageInfo missing contract key {pkey!r}"
