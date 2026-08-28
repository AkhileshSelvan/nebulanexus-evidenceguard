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
extraction = extract(document, image_paths=[...])   # -> Extraction (contract §2)
```

`extract()` must always return a contract-valid `Extraction`, even on failure
(empty `fields`, `text_confidence = 0.0`). Raising is allowed only for truly
unexpected errors — the backend will convert it to a `ModuleError`.

## Dependencies

None yet. Add OCR libs (`pytesseract`, `rapidocr-onnxruntime`, a cloud client,
…) in a later checkpoint and list them in `backend/requirements.txt` under an
`# ocr` comment, with a one-line justification in the PR.
