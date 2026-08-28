# EvidenceGuard

**AI-Assisted Document Verification & Fraud Detection Platform**
Built for the OBLIVION 2026 hackathon.

> **Core principle:** _"Verify the evidence, not just the document."_

Most verification tools stop at "is this a valid-looking PDF?" EvidenceGuard goes
further: it treats every submitted document as a piece of **evidence** and asks
whether the evidence holds together — internally (pixels, fonts, metadata) and
externally (does it agree with the other documents in the same case?).

---

## 1. Purpose

Give a reviewer a single, explainable verdict on a bundle of documents
(e.g. an ID + a payslip + a bank statement) by combining:

- **Text extraction** — what does the document *say*?
- **Forensic analysis** — has the *image/file* been manipulated?
- **Metadata analysis** — does the *file's history* look plausible?
- **Cross-document consistency** — do the documents *agree with each other*?
- **Risk scoring** — how much of a problem is this, on a 0–100 scale?
- **Recommendation + explanation** — what should the human do, and *why*?

The output is designed to be handed to a non-technical reviewer. Every score
carries human-readable reasons and links back to the signals that produced it.

---

## 2. Core pipeline

```
                 ┌────────────────────────────────────────────────────────┐
                 │                     backend (FastAPI)                   │
                 │                                                        │
 upload  ──────▶ │  ingest → normalize document → fan out to modules ──┐  │
 (1..n files)    │                                                     │  │
                 │   ┌─────────────┐  ┌─────────────┐  ┌────────────┐   │  │
                 │   │  modules/   │  │  modules/   │  │ modules/   │   │  │
                 │   │    ocr      │  │  forensics  │  │  metadata* │   │  │
                 │   └──────┬──────┘  └──────┬──────┘  └─────┬──────┘   │  │
                 │          │                │               │          │  │
                 │          └────────┬───────┴───────┬───────┘          │  │
                 │                   ▼                ▼                  │  │
                 │           modules/consistency   (per-bundle)         │  │
                 │                   │                                  │  │
                 │                   ▼                                  │  │
                 │              modules/risk  → recommendation + why ◀──┘  │
                 │                   │                                     │
                 └───────────────────┼─────────────────────────────────────┘
                                     ▼
                        frontend (React) renders the report
```

\* `metadata` extraction lives inside `modules/forensics` for now (file-level
signal). It is called out separately in the API contract so it can be split into
its own module later without breaking consumers.

**Stage by stage**

| # | Stage | Owner module | Produces (see `docs/API_CONTRACT.md`) |
|---|-------|--------------|----------------------------------------|
| 1 | Ingest & normalize | `backend` | `document` |
| 2 | Text extraction | `modules/ocr` | `extraction` |
| 3 | Image/file forensics | `modules/forensics` | `forensics`, `metadata` |
| 4 | Cross-document consistency | `modules/consistency` | `consistency` |
| 5 | Risk aggregation | `modules/risk` | `risk`, `recommendation`, `explanation` |
| 6 | Presentation | `frontend` | — |

---

## 3. Module responsibilities

Each module is an **independent Python package** under `modules/`. A module:

- receives a normalized `document` (and, for consistency/risk, the outputs of the
  earlier stages),
- returns **only** its slice of the shared JSON contract,
- must not import from `backend/` or from sibling modules — the backend is the
  only orchestrator.

| Module | Responsibility | Explicitly NOT responsible for |
|--------|----------------|-------------------------------|
| `modules/ocr` | Extract raw text, key/value fields, tables, per-field confidence and bounding boxes. | Deciding if a value is *correct* or *fraudulent*. |
| `modules/forensics` | Pixel/file-level manipulation signals: ELA, copy-move, noise, compression ghosts, splicing, plus PDF/EXIF **metadata** extraction & plausibility. | Reading the document's *meaning*; comparing across documents. |
| `modules/consistency` | Compare extracted fields **across** all documents in a bundle: name/DOB/address match, date ordering, arithmetic (totals), template/issuer expectations. | Single-document image forensics; final risk math. |
| `modules/risk` | Aggregate every upstream signal into a `risk` score (0–100) + severity band, then derive a `recommendation` and a plain-language `explanation`. | Producing raw signals — it only *combines* them. |

**Frontend / backend**

| Area | Responsibility |
|------|----------------|
| `backend` | HTTP API, file ingest, normalization, module orchestration, response assembly, health check. No detection logic of its own. |
| `frontend` | Upload UI, render the verification report, show per-signal explanations. No detection logic; talks only to the backend API. |

---

## 4. Development rules

1. **The contract is law.** `docs/API_CONTRACT.md` defines every shared object.
   Change the doc + get sign-off *before* changing a payload shape.
2. **Modules are libraries, not services.** Pure functions in / dict out. No
   Flask/FastAPI inside a module, no network calls to siblings.
3. **One orchestrator.** Only `backend/` imports modules and wires them together.
4. **Stay in your lane.** OCR, forensics, consistency, risk, frontend, backend
   each own their directory. Cross-directory edits need a heads-up in the team
   channel.
5. **Frontend and backend run independently.** `frontend/` must build and boot
   with the backend down (it just shows "backend offline").
6. **Every score needs a reason.** No bare numbers in the API — attach the
   signals that produced them.
7. **No scope creep yet.** For this checkpoint: **no** real OCR, forensic,
   or AI implementation, **no** auth, **no** database, **no** deployment config.
   Stubs return contract-shaped placeholder data.
8. **Keep dependencies minimal.** Adding a package = a line in the PR description
   explaining why.
9. **Commit per module.** Small, reviewable commits scoped to one directory.

---

## 5. Repository layout

```
frontend/          React + Vite + TypeScript + Tailwind SPA
backend/           FastAPI app: ingest, orchestrate, serve the report
modules/
  ocr/             text & field extraction        (stub)
  forensics/       image forensics + metadata     (stub)
  consistency/     cross-document checks           (stub)
  risk/            risk score, recommendation, why (stub)
data/
  demo/            sample documents & expected outputs for the demo
docs/
  API_CONTRACT.md  the shared JSON contract — read this first
```

---

## 6. Running locally

Prereqs: **Python 3.11+**, **Node 20+**.

### Backend

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- Health check: <http://localhost:8000/health>
- API docs (auto): <http://localhost:8000/docs>

### Frontend

```bash
cd frontend
npm install
npm run dev
```

- App: <http://localhost:5173>
- The dev server proxies `/api/*` and `/health` to `http://localhost:8000`.
- Override the backend URL with `VITE_API_BASE_URL` in `frontend/.env`.

The two run independently. Start either one on its own; the frontend degrades to
"backend offline" when the API is unreachable.
