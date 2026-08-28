# `modules/risk`

**Owns:** `risk` (§6, per-document **and** per-bundle), `recommendation` (§7),
`explanation` (§8) of `docs/API_CONTRACT.md`.

> **This is a risk-triage engine.** It does not prove a document genuine and it
> does not prove one fraudulent. It ranks how much human attention a bundle
> deserves and shows its working. The score is an ordinal triage number, **not**
> a calibrated probability of fraud.

## Responsibility

1. **`score_document(document_id, forensics, metadata, extraction=None)`** → `Risk` (scope `"document"`)
2. **`score_bundle(bundle_id, document_risks, consistency)`** → `Risk` (scope `"bundle"`)
3. **`recommend(bundle_risk, *, coverage_gaps=None)`** → `Recommendation`
4. **`explain(bundle_risk, document_risks, consistency, *, coverage_gaps=None)`** → `Explanation`

All parameters after the id are optional — a missing or malformed section is
never counted, and never counted *against* the subject.

## The model: bounded log-additive noisy-OR

```
p_i = (signal_score / 100) × source_weight × confidence     # normalise
u_i = −ln(1 − p_i)                                          # evidence mass (nats)
U   = Σ u_i                                                 # after dedupe + source ceilings
S   = 100 × (1 − e^(−U))                                    # the score
contribution_i = S × (u_i / U)                              # exact attribution
```

**Why this one**, over the alternatives the foundation listed:

| Property | Why it matters here |
|---|---|
| **Bounded by construction** | `1 − e^(−U) < 1` always. No clamping — and no clamping means attribution is never silently destroyed. A weighted sum needs a clamp and loses this. |
| **Exactly traceable** | `Σ contribution_i == S`. A judge can audit the arithmetic by hand. Plain noisy-OR is multiplicative and can't offer this. |
| **Diminishing returns** | Twenty trivial signals can't impersonate certainty. |
| **Missing evidence is neutral** | An absent signal contributes no term; the product is unchanged. Absence never raises the score. |
| **Deterministic** | Pure arithmetic over sorted inputs. Same input → identical output, every run. |
| **Lone signals can't convict** | With one term `S = 100 × p` exactly, so the largest source weight *is* the ceiling for any single signal. |

## Weights and ceilings

Every number the engine uses lives at the top of `scorer.py`.

| Source | Weight | Ceiling | Lone signal | Source saturated (doc) | Source saturated (bundle) | Meaning |
|---|---|---|---|---|---|---|
| `consistency` | 0.60 | 0.72 | **60** high → review | n/a (bundle-scoped) | **72.00** high → review | Cross-document contradiction — hardest to explain away |
| `forensics` | 0.55 | 0.70 | **55** high → review | **70.00** high → review | **64.06** high → review | Pixel/file tampering evidence |
| `metadata` | 0.35 | 0.55 | **35** medium → review | **55.00** high → review | **49.27** medium → review | Circumstantial; edit gaps have innocent causes |
| `ocr` | 0.15 | 0.30 | **15** low | **8.98** low | **7.69** low → accept | Document *quality*, not fraud evidence — nudges only |

Measured values, not intended ones — they are asserted in
`test_no_single_source_can_independently_reject`.

### The two policy guarantees, and the arithmetic that enforces them

**1. No single *signal* can prove fraud.** With one term the score is exactly
`100 × p`, so the largest **weight** is the ceiling for any lone signal. The
largest is `consistency` at 0.60 → **60**, which is `high` → *review*. Nothing a
single signal can say reaches the 75 needed to recommend rejection.

**2. No single *source* can independently produce a reject.** Every entry in
`SOURCE_PROBABILITY_CEILING` is **below 0.75**, so a source firing every signal
it has, at maximum strength and confidence, still lands in `high` → *review* at
worst. The strongest is `consistency` at **72.00**.

**3. `critical` / `reject` therefore requires corroboration** from at least two
independent sources. It is not gated by an `if` — it falls out of the fusion:

| Combination | Score | Outcome |
|---|---|---|
| forensics alone (saturated) | 64.06 | review |
| consistency alone (saturated) | 72.00 | review |
| **forensics + consistency** | **89.94** | **reject** |
| realistic 3-source bundle | 93.22 | reject |

Severity bands and severity→decision come from `modules/contract.py`
(`SEVERITY_BANDS`, `DEFAULT_DECISION_FOR_SEVERITY`) — never redefined here.

## Policy guarantees

- **No double counting** — dedupe on `(source, signal_id, document_id)`, plus a
  per-source mass ceiling so one noisy module can't saturate the score.
- **No double counting at bundle level** — document evidence is recovered by
  *inverting* each document's own attribution (`u_i = U_d × contribution_i / S_d`),
  not re-read from the raw sections, so confidence/dedupe/ceilings already
  applied per document are preserved rather than reapplied. It then enters at
  `DOCUMENT_MASS_DAMPING = 0.85`. Consistency is genuinely new bundle-level
  information, so it enters at full weight.
- **Clean ≠ certain** — a bundle with no signals reports `confidence = 0.6`, not
  1.0. "Nothing fired" can mean "clean" or "nobody looked".
- **Confidence is never 1.0** — capped at `MAX_RECOMMENDATION_CONFIDENCE = 0.95`.
- **Coverage gaps lower confidence, never raise score** — pass
  `coverage_gaps=["ocr"]` when a module couldn't run.
- **Unreported confidence** (a module sends `score > 0` but `confidence == 0.0`)
  is treated as `UNREPORTED_CONFIDENCE = 0.5`, not as certainty and not as zero.
- **Document tagging is lossless** — bundle contributions tag a signal with the
  document that raised it as `"<signal_id>@<document_id>"`. Producing modules may
  use `@` in their own ids, so the tag is split from the **right**; an id like
  `checks@issuer_domain` survives a round trip intact. Documented in
  `docs/API_CONTRACT.md` §6.

## Reason codes

`REASON_CODES` is the stable vocabulary; the sentence after the code may be
reworded freely. `NO_SIGNALS`, `FORENSIC_SIGNALS`, `METADATA_SIGNALS`,
`CONSISTENCY_SIGNALS`, `OCR_QUALITY`, `CORROBORATED`, `SINGLE_SOURCE`,
`COVERAGE_GAP`, `NEAR_BOUNDARY`.

Issue #7's `LOW_RISK / REVIEW_REQUIRED / HIGH_RISK` tiers map onto the existing
`recommendation.decision` (`accept` / `review` / `reject`) — no new contract
field was added for them.

## Entry point

```python
from modules.risk import score_document, score_bundle, recommend, explain
```

## Tests

```bash
python -m pytest modules/risk/tests -q
```

## Dependencies

None beyond the standard library (`math`). No FastAPI, no sibling modules, no
network calls.
