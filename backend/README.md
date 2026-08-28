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
  routers/
    health.py       GET /health
    verify.py       GET /api/v1/ping, POST /api/v1/verify
tests/
  test_smoke.py     app boots, /health works, /verify returns a contract-shaped report
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

Runs standalone — no database, no frontend, no external services.

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
| `POST` | `/api/v1/verify` | `multipart/form-data`: `files` (1..n), optional `declared_types`. Returns `VerificationReport`. **Stubbed** — real ingest, placeholder analysis. |

## Adding module dependencies

Put them in `requirements.txt` under a `# <module-name>` comment with a
one-line reason, and mention it in the PR description.
