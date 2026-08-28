# `modules/consistency`

**Owns:** `consistency` — §5 of `docs/API_CONTRACT.md`.

## Responsibility

Given every document's `extraction` output, check that the documents **agree
with each other**:

- `name_match`, `dob_match`, `address_match` across documents
- `document_number_reuse` (same number on things that shouldn't share one)
- `date_ordering` — issue < expiry, pay-period start < end
- `amount_arithmetic` — gross − deductions = net, statement lines sum to totals
- `issuer_expected`, `period_overlap`, `template_match`

Each check reports `status` (`pass` / `warn` / `fail` / `not_applicable`), a
`score` (0–100 concern), `confidence`, the `observed` values it compared, and
which `document_ids` it tied together.

## Not your job

- Single-document image forensics (`forensics`).
- Extracting the fields you consume (`ocr`).
- Final risk math (`risk`).

## Entry point

```python
from modules.consistency import check_consistency
consistency = check_consistency(documents, extractions)   # -> Consistency (§5)
```

`documents[i]` and `extractions[i]` are order-aligned. Return a contract-valid
`Consistency` even with 0 or 1 documents (all checks `not_applicable`).

## Dependencies

None yet. Likely later: `rapidfuzz` (fuzzy name/address matching),
`python-dateutil`. Add under `# consistency` in `backend/requirements.txt`.
