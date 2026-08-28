# `modules/risk`

**Owns:** `risk` (§6, per-document **and** per-bundle), `recommendation` (§7),
`explanation` (§8) of `docs/API_CONTRACT.md`.

## Responsibility

Combine every upstream signal into decisions a human can act on:

1. **`score_document(document_id, forensics, metadata)`** → `Risk` (scope
   `"document"`).
2. **`score_bundle(bundle_id, document_risks, consistency)`** → `Risk` (scope
   `"bundle"`).
3. **`recommend(bundle_risk)`** → `Recommendation` (`accept` / `review` /
   `reject` + reasons).
4. **`explain(bundle_risk, document_risks, consistency)`** → `Explanation`
   (narrative + evidence links + glossary).

Every number must be traceable: fill `contributions[]` on each `Risk` and
`evidence[]` on each explanation factor so the UI can show *why*.

## Not your job

- Producing raw signals — you only weight and combine what `ocr`, `forensics`
  and `consistency` return.

## The open decision

`_aggregate()` in `scorer.py` is stubbed to `0.0`. It carries a `TODO` spelling
out four candidate models (weighted sum, noisy-or, max+dampened, small rule
set) and their trade-offs. **Pick one, implement it, justify it in the PR.**
Keep it deterministic — the demo re-runs the same bundle repeatedly.

Severity bands and the severity→decision default live in `modules/contract.py`
(`SEVERITY_BANDS`, `DEFAULT_DECISION_FOR_SEVERITY`) — don't redefine them here.

## Entry point

```python
from modules.risk import score_document, score_bundle, recommend, explain
```

## Dependencies

None expected — this module is pure Python arithmetic over the other sections.
