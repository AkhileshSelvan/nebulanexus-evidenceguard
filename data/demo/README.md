# `data/demo`

Curated sample documents and their **expected** verification outcomes, used to
drive the hackathon demo and to sanity-check modules.

## Layout (to be filled in)

```
data/demo/
  bundles/
    clean-applicant/          a bundle that should score LOW / "accept"
      id_card.png
      payslip.pdf
      bank_statement.pdf
      expected.json           trimmed VerificationReport fields to assert against
    tampered-payslip/         a bundle that should score HIGH / "review|reject"
      ...
  README.md
```

## Rules

- Only **synthetic or properly consented** documents. No real personal data.
- Keep files small (< 2 MB each) so the repo stays light.
- `expected.json` holds just the fields a test cares about (e.g.
  `recommendation.decision`, `risk.severity`, key `consistency.checks[].status`),
  not a full report snapshot.

Nothing here yet — add bundles alongside the module that needs them.
