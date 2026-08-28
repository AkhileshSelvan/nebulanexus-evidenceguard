# EvidenceGuard — Backend

FastAPI service that ingests document bundles, orchestrates the analysis
modules, and serves a `VerificationReport` (see `../docs/API_CONTRACT.md`).

The backend contains **no detection logic** — it only ingests, calls modules,
and assembles their output.

## Layout

```
app/
  main.py           FastAPI app + CORS + router wiring
  config.py         constants / env-driven settings
  orchestrator.py   the ONLY importer of ../modules/* ; builds the report
  db.py             SQLite connection + schema (cases, audit_log)
  storage.py        case persistence — the only writer of `cases`
  audit.py          append-only audit trail — the only writer of `audit_log`
  routers/
    health.py       GET /health
    verify.py       GET /api/v1/ping, POST /api/v1/verify (persists a case)
    cases.py        GET /api/v1/cases[/{id}], POST .../decision, GET .../audit
tests/
  test_smoke.py     app boots, /health works, /verify returns a contract-shaped report
  test_cases.py     case storage, reviewer decisions, audit trail
requirements.txt        runtime deps (minimal)
requirements-dev.txt    + pytest, httpx
```

## Run

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- Health:   <http://localhost:8000/health>
- Ping:     <http://localhost:8000/api/v1/ping>
- OpenAPI:  <http://localhost:8000/docs>

Runs standalone — no frontend, no external services. State lives in a local
SQLite file (`evidenceguard.db` by default, next to wherever you run
`uvicorn` from). Point it elsewhere with `EG_DB_PATH`; the test suite always
uses `EG_DB_PATH=:memory:` (see `tests/conftest.py`), so running `pytest`
never touches your dev DB.

## Test

```bash
pip install -r requirements-dev.txt
pytest
```

## Endpoints (foundation)

| Method | Path | Notes |
|--------|------|-------|
| `GET` | `/health` | `{ status, service, version, time }` |
| `GET` | `/api/v1/ping` | `{ "message": "pong" }` |
| `POST` | `/api/v1/verify` | `multipart/form-data`: `files` (1..n), optional `declared_types`. Returns `VerificationReport` and persists it as a case. **Analysis is stubbed** — real ingest, placeholder findings. |
| `GET` | `/api/v1/cases` | `?limit=&offset=` — newest-first case summaries |
| `GET` | `/api/v1/cases/{report_id}` | Full stored report + current reviewer decision |
| `POST` | `/api/v1/cases/{report_id}/decision` | Body: `{ decision, reviewer_name, notes? }`. Overwrites the case's current decision; always audited |
| `GET` | `/api/v1/cases/{report_id}/audit` | Full append-only audit trail for the case, oldest first |

See `docs/API_CONTRACT.md` §12 for exact shapes.

## Adding module dependencies

Put them in `requirements.txt` under a `# <module-name>` comment with a
one-line reason, and mention it in the PR description.
