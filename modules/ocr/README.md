# `modules/ocr`

**Owns:** `extraction` — §2 of `docs/API_CONTRACT.md`.

## Responsibility

- Turn a normalized `Document` into text + structured fields.
- Populate `full_text`, `fields[]` (using the shared field-key vocabulary in the
  contract), `tables[]`, and per-field `confidence` + `bbox`.

## Not your job

- Deciding whether a value is *right* or *fraudulent* — that's `consistency`.
- Any image-manipulation analysis — that's `forensics`.

## Entry point

```python
from modules.ocr import extract
extraction = extract(document, data)   # data: bytes = the raw uploaded file
                                        # -> Extraction (contract §2)
```

`extract()` must always return a contract-valid `Extraction`, even on failure
(empty `fields`, `text_confidence = 0.0`). Raising is allowed only for truly
unexpected errors — the backend will convert it to a `ModuleError`.

This module owns rasterization too: `extract()` decodes `data` itself
(`rasterize.py` — Pillow for JPG/JPEG/PNG, PyMuPDF for PDF), so the backend
does not need to pre-render pages or pass image paths.

## Dependencies

`pillow`, `pytesseract`, `pymupdf` — pinned in `backend/requirements.txt`
under the `# ocr` comment. `pytesseract` additionally needs the **Tesseract
OCR binary** on the host (`apt install tesseract-ocr`, or set `TESSERACT_CMD`
if it's installed somewhere non-standard). If Tesseract isn't found, `extract()`
still returns a valid (empty-text) `Extraction` with a warning — it never
fabricates output or raises for a missing binary.
