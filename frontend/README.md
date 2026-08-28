# EvidenceGuard — Frontend

React + Vite + TypeScript + Tailwind CSS single-page app. Foundation build:
one page showing the app name and live backend connection status.

## Layout

```
index.html
vite.config.ts        dev server + /health, /api proxy to the backend
tailwind.config.js     Tailwind config (brand accent under `guard.*`)
postcss.config.js
src/
  main.tsx            React entry
  App.tsx             the "EvidenceGuard" page + connection card
  api.ts             backend client (checkHealth)
  index.css          Tailwind directives
```

## Run

```bash
npm install
npm run dev        # http://localhost:5173
```

Runs **independently of the backend**. If the API is down the page shows
"Backend offline" with a Re-check button.

## Build & typecheck

```bash
npm run build       # tsc -b && vite build  -> dist/
npm run preview     # serve the production build
npm run typecheck
```

## Config

| Env var | Default | Purpose |
|---------|---------|---------|
| `VITE_API_BASE_URL` | `""` (same-origin, dev proxy) | Backend origin for non-dev environments |
| `VITE_PROXY_TARGET` | `http://localhost:8000` | Where the dev server proxies `/health` and `/api` |

## Talking to the backend

`src/api.ts` is the single place that knows the backend exists. Add new calls
there and keep response types in sync with `../docs/API_CONTRACT.md`.
