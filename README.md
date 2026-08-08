<h1 align="center">Musha</h1>

<div align="center">
<p><em>Web content and DOM analysis — part of the <a href="https://github.com/xwebanalysis">XWA ecosystem</a></em></p>
</div>

<hr>

<p><strong>Status: <em>In development</em></strong> (v0.1.0)</p>

<p>Analysis of web content structure and third-party footprint: resource inventory, provider fingerprinting, structural diffing and content drift.</p>

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | Angular 22 (standalone, SCSS, Node 24) — Nothing Design System |
| Backend | FastAPI (Python 3.12+) + SQLAlchemy 2 + PostgreSQL/SQLite |
| Data contracts | xwa-sdk (Event envelope over WebSocket) |

## Features (current)

- Third-party resource inventory: scripts, stylesheets, iframes and preconnects extracted from the DOM
- Provider fingerprinting: 40+ vendor rules (Google Tag Manager, jsDelivr, Cloudflare, Sentry, Shopify, ...) with category classification
- Resource attributes: async/defer flags, SRI integrity, crossorigin, protocol-relative and relative URL resolution, deduplication
- Live streaming of inventory progress as xwa-sdk Events over WebSocket (`/api/content/live`)
- Client-side JSON export of analysis results

## Quick start (Docker)

```bash
./musha.sh docker all
```

- Frontend: http://localhost:4200
- Backend API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs

## Quick start (local)

```bash
./musha.sh local backend    # terminal 1 — FastAPI on :8000 (SQLite)
./musha.sh local frontend   # terminal 2 — Angular on :4200
```

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Service info |
| GET | `/api/health` | Health check with database status |
| POST | `/api/content/inventory` | Run the resource inventory on a target |
| WS | `/api/content/live?target=...` | Stream inventory events (xwa-sdk Event format) |

## Documentation

- [docs/README.md](docs/README.md) — documentation index
- [docs/architecture.md](docs/architecture.md) — stack, layout and data flow
- [docs/api.md](docs/api.md) — REST and WebSocket API reference
- [docs/development.md](docs/development.md) — execution modes, environment variables, verification

## Roadmap

See [ROADMAP.md](ROADMAP.md) — next: structural diffing, content drift detection, production hardening.
