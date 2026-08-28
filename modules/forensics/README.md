# `modules/forensics`

**Owns:** `forensics` (§3) and `metadata` (§4) of `docs/API_CONTRACT.md`.

## Responsibility

- **`analyze()`** — pixel/file-level manipulation signals on a single document:
  ELA, copy-move, noise inconsistency, double compression, splicing boundaries,
  font substitution, PDF text-layer vs. pixel mismatch, annotation overlays.
- **`extract_metadata()`** — pull embedded metadata (PDF info dict / XMP, EXIF,
  Office core props), derive `created_at` / `modified_at` / editor chain, and
  raise plausibility signals (future timestamps, edit-after-create gaps, image
  editors in the tool chain, missing expected metadata).

Each signal carries its own `score` (0–100), `confidence` (0–1), `passed` flag
and a human-readable `detail`. The module rolls its signals up into a section
`score` but does **not** decide overall risk.

## Not your job

- Reading the document's meaning (`ocr`).
- Comparing values across documents (`consistency`).
- Final risk / recommendation (`risk`).

## Entry points

```python
from modules.forensics import analyze, extract_metadata

forensics = analyze(document, image_paths=[...])       # -> Forensics  (§3)
metadata  = extract_metadata(document, file_path=...)  # -> Metadata   (§4)
```

Both must return contract-valid dicts even when they can't do their job
(empty `signals`, `score = 0.0`).

## Dependencies

None yet. Likely later: `pillow`, `numpy`, `pikepdf`, `exifread` / `piexif`,
`hachoir`. Add them under `# forensics` in `backend/requirements.txt`.
