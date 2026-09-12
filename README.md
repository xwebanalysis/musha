<h1 align="center">Musha</h1>

<div align="center">
<p><em>Web content and DOM analysis — part of the <a href="https://github.com/xwebanalysis">XWA ecosystem</a></em></p>
</div>

<hr>

<p><strong>Status: <em>In development</em></strong> (v0.2.0)</p>

<p>Analysis of web content structure and third-party footprint: resource inventory, provider fingerprinting, persisted history and server-side exports.</p>

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | Angular 22 (standalone, SCSS, Node 24) — Nothing Design System |
| Backend | FastAPI (Python 3.13) + SQLAlchemy 2 + SQLite (PostgreSQL optional) |
| Data contracts | xwa-sdk (shared `Event`/`Error` envelopes over WebSocket) |

## Features (current)

- Third-party resource inventory: scripts, stylesheets, iframes and preconnects extracted from the DOM
- Provider fingerprinting: 45+ vendor rules (Google Tag Manager, jsDelivr, Cloudflare, Sentry, Shopify, ...) with category classification
- Resource attributes: async/defer flags, SRI integrity, crossorigin, protocol-relative and relative URL resolution, deduplication
- Live streaming of inventory progress as xwa-sdk Events over WebSocket (`/api/content/live`) with a terminal log and phase row in the UI
- Persisted analysis history: list, detail, per-analysis delete and delete-all endpoints
- Server-side exports: `GET /api/analyses/{id}/export?format=json|csv` (downloadable via `Content-Disposition`) plus client-side JSON/CSV/PDF (jsPDF, lazy-loaded)
- Angular UI structured as `core/` + `shared/` + `features/` with lazy routes and a sidebar: analyzer (`/`), history list/detail (`/history`, `/history/:id`) and exports console (`/exports`)
- Nothing Design System: self-hosted Doto / Space Grotesk / Space Mono fonts, `--gold` token, dark/light mode, ALL CAPS labels
- Optional JWT auth (`MUSHA_JWT_SECRET`) + in-memory rate limiting (`MUSHA_RATE_LIMIT_MAX`, default 120/min)
- Configurable CORS (`XWA_CORS_ORIGINS`) with credentials disabled

## Quick start (local, default)

```bash
./musha.sh local all        # backend :8020 (SQLite) + frontend :4220
```

or in two terminals:

```bash
./musha.sh local backend    # terminal 1 — FastAPI on :8020 (SQLite)
./musha.sh local frontend   # terminal 2 — Angular on :4220
```

- Frontend: http://localhost:4220
- Backend API: http://localhost:8020
- Swagger docs: http://localhost:8020/docs
- SQLite database: `backend/musha.db` (WAL, foreign keys, busy timeout 5000 ms)

The script creates/updates `backend/.venv` with `uv` (Python 3.13), installs the
sibling `xwa-sdk` binding in editable mode when available, and falls back to the
git repository documented in `backend/requirements.txt` otherwise.

## Quick start (Docker, PostgreSQL)

```bash
./musha.sh docker all       # frontend :4220, backend :8020, PostgreSQL :5442
```

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Service info |
| GET | `/api/health` | Health check with real database status (`200`/`503`) |
| POST | `/api/content/inventory` | Run the resource inventory on a target |
| GET | `/api/analyses` | List the 50 most recent analyses |
| GET | `/api/analyses/{id}` | Analysis detail with resources |
| GET | `/api/analyses/{id}/export?format=json\|csv` | Download an analysis (attachment) |
| DELETE | `/api/analyses/{id}` | Delete one analysis |
| DELETE | `/api/analyses` | Delete all analyses |
| POST | `/api/auth/token` | Issue a JWT (when `MUSHA_JWT_SECRET` is set) |
| WS | `/api/content/live?target=...` | Stream inventory events (xwa-sdk `Event`) |

## Documentation

- [docs/README.md](docs/README.md) — documentation index
- [docs/architecture.md](docs/architecture.md) — stack, layout and data flow
- [docs/api.md](docs/api.md) — REST and WebSocket API reference
- [docs/development.md](docs/development.md) — execution modes, environment variables, verification

## Roadmap

See [ROADMAP.md](ROADMAP.md) — next: structural diffing, content drift detection, data-leakage channels.
