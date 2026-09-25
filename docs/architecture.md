# Architecture

## Overview

Musha is a two-tier web application: an Angular single-page application and a FastAPI service. The backend owns the analysis pipeline and persistence; the frontend renders the inventory.

```
+--------------------+      HTTP/JSON       +---------------------------+
| Angular 22 SPA     | -------------------> | FastAPI (uvicorn)          |
| (localhost:4220)   | <------------------- | (localhost:8020)           |
+--------------------+    WebSocket        +--------------+-------------+
                                                    |     |
                                                    v     v
                                              SQLite (default) / PostgreSQL
```

## Backend

Layout:

```
backend/
├── app/
│   ├── __init__.py
│   ├── analyzer.py      # resource extraction; delegates provider fingerprinting
│   ├── vendor_db.py     # vendor classification DB (JSON rules + scored matching)
│   ├── diffing.py       # structural diff: URL normalization + added/removed/modified
│   ├── drift.py         # content drift: consecutive analyses, severity + alerts
│   ├── data/
│   │   └── vendors.json # 45 vendors / 47 fragments migrated from legacy rules
│   ├── database.py      # engine setup, SQLite/PostgreSQL switch, ping, PRAGMAs
│   ├── main.py          # FastAPI app, REST routes, WebSocket endpoint
│   ├── models.py        # SQLAlchemy ORM models
│   ├── schemas.py       # Pydantic v2 request/response models
│   └── security.py      # CORS config, optional JWT auth, rate limiting
├── tests/               # analyzer/vendor-db/diffing/drift units + API integration
├── Dockerfile           # python:3.13-slim (PostgreSQL mode)
├── requirements.txt             # runtime (SQLite by default)
├── requirements-postgres.txt    # + psycopg2-binary (docker mode)
└── requirements-dev.txt         # + pytest/pytest-asyncio/anyio (tests)
```

### Components

- **analyzer.py** — the analysis core:
  - `inventory_resources(html, page_url)` — extracts `<script src>`, `<iframe src>`, stylesheet and preconnect `<link>` elements. Relative and protocol-relative URLs are resolved against the page URL; `data:`/`blob:`/`about:` URLs are skipped; duplicates are removed.
  - Captures `integrity` (SRI), `crossorigin`, `async` and `defer` attributes.
  - `fingerprint(url)` — delegates to `vendor_db`, returning `(provider, category)`.
- **vendor_db.py / data/vendors.json** — the vendor classification database. One JSON entry per provider (category + URL fragments); matching is scored (host exact 100 > host suffix 90 > host substring 80 > path 60 > url 40) and the best-scoring vendor wins. Loaded and validated at startup.
- **diffing.py** — `normalize_url()` strips fragment + query-string noise tokens (utm_*, gclid, fbclid, nonce, cache-busters, timestamps) and lowercases scheme/host; `diff_resources()` classifies resources as added/removed/modified (attribute or provider change) and computes a Dice similarity score.
- **drift.py** — `analyze_drift()` compares consecutive analyses of a domain: resource-count delta, provider additions/removals, per-step severity (low/medium/high) and alert text.
- **models.py** — two tables: `content_analyses` (the analysis session, statuses `PENDING|RUNNING|COMPLETED|ERROR|CANCELLED`) and `third_party_resources` (one row per resource with type, URL, host, attributes, provider and category).
- **database.py** — SQLite by default (`DB_DRIVER=sqlite`, path `DB_PATH`) or PostgreSQL (`DB_DRIVER=postgresql`). SQLite connections enable `foreign_keys`, `journal_mode=WAL` and `busy_timeout=5000`. `ping()` backs the health endpoint and `wait_for_db()` gates startup in PostgreSQL mode.
- **security.py** — `cors_settings()` builds the CORSMiddleware arguments from `XWA_CORS_ORIGINS` (localhost/LAN regex by default, credentials disabled), `auth_middleware` enforces an optional HS256 Bearer token, `rate_limit_middleware` implements a 120 req/min sliding window (`/api/health` exempt), and `validate_ws_token()` guards WebSockets via `?token=`.
- **main.py** — REST routes (including `GET /api/analyses/{id}/diff?against=` and `GET /api/targets/{domain}/drift`), WebSocket, global exception handlers that convert `HTTPException`/validation errors into the xwa-sdk `Error` envelope, and lifespan schema creation.

### Analysis flow

1. The client calls `POST /api/content/inventory` with a target.
2. A `ContentAnalysis` row is created with status `RUNNING`.
3. The page is fetched (redirects followed), the title captured, and resources are extracted and fingerprinted.
4. Resources are persisted and linked to the analysis; status becomes `COMPLETED` (or `ERROR` with the message stored and a `502` envelope returned).

The WebSocket variant (`/api/content/live`) persists the analysis first and
streams xwa-sdk `Event` envelopes with the **persisted id** as `analysis_id`
(string), monotonic `seq` and UTC `ts`: `analysis_started`,
`analysis_progress`, one `item_found` per resource, then
`analysis_completed`/`analysis_error`. The same resources are persisted, so a
live run appears in `GET /api/analyses` afterwards.

## Frontend

Layout (core / shared / features):

```
frontend/
├── src/
│   ├── app/
│   │   ├── app.config.ts       # providers (router, HttpClient)
│   │   ├── app.routes.ts       # lazy routes: '', 'history', 'history/:id', 'exports'
│   │   ├── app.ts/html/scss    # sidebar shell: brand, nav, health, theme, locale
│   │   ├── core/
│   │   │   ├── api.service.ts  # typed REST/WS client + xwa-sdk Event types
│   │   │   ├── live.service.ts # WebSocket wrapper + parseLiveEvent()
│   │   │   ├── export.service.ts # client JSON/CSV/PDF (jsPDF lazy)
│   │   │   ├── i18n.service.ts # en/es labels (Angular Signals)
│   │   │   └── theme.service.ts# dark/light mode with Angular Signals
│   │   ├── shared/
│   │   │   ├── terminal/       # live log panel
│   │   │   ├── metric-card/    # Doto hero metric
│   │   │   ├── status-badge/   # PENDING/RUNNING/COMPLETED/ERROR
│   │   │   ├── export-actions/ # client JSON/CSV/PDF + server JSON/CSV
│   │   │   ├── charts/         # xwa-chart: pure-SVG donut/h-bars/bars/line
│   │   │   └── detail-table/   # generic flat data table
│   │   └── features/
│   │       ├── analyzer/       # target input, REST + WS runs, phase row, terminal
│   │       ├── history/        # list + detail view (resource sections, charts, diff, drift)
│   │       └── exports/        # export console for recent analyses
│   ├── environments/
│   │   └── environment.ts      # apiBaseUrl / wsBaseUrl (host resolved at runtime)
│   ├── _fonts.scss             # self-hosted Doto / Space Grotesk / Space Mono
│   ├── styles.scss             # Nothing tokens (incl. --gold)
│   └── index.html              # no Google Fonts at runtime
├── public/fonts/               # woff2 files served as static assets
├── scripts/test.sh         # maps `npm test -- --run` onto the Angular builder
├── Dockerfile              # node:24 (dev server)
├── nginx.conf              # SPA fallback for production serving
└── package.json            # Angular 22.1 + jsPDF
```

- Navigation is a left sidebar (`app.html`) with three lazy-loaded routes: analyzer
  (`/`), history list/detail (`/history`, `/history/:id`) and the exports console
  (`/exports`). The analyzer keeps the target form and, after a run, renders the
  same detail component used by `/history/:id`.
- **Live WebSocket**: the analyzer can run `/api/content/live` and consumes the
  xwa-sdk `Event` envelopes (`analysis_started`, `analysis_progress`,
  `item_found`, `analysis_completed`, `analysis_error`) through `LiveService`.
  `parseLiveEvent()` validates the frame before it reaches the component. The
  synchronous `POST /api/content/inventory` remains as fallback.
- **Exports**: the detail view offers client-side JSON/CSV/PDF (jsPDF is
  dynamically imported, so it never lands in the initial bundle) plus server-side
  JSON/CSV links to `/api/analyses/{id}/export`. The exports feature applies the
  same actions to any recent analysis.
- **Charts** (XWA chart spec, pure SVG): the detail view renders a resources-by-type
  donut, providers-by-category h-bars and resource attribute flag bars; the
  history view renders an analyses-per-day line chart and a status donut.
- **Diff / drift**: the detail view offers a DIFF selector
  (`GET /api/analyses/{id}/diff?against=`) and a DRIFT panel per domain
  (`GET /api/targets/{domain}/drift`), both rendered as Nothing-styled tables.
- **Zoneless change detection**: the app runs without zone.js, so every async
  callback that mutates component state calls `ChangeDetectorRef.markForCheck()`
  (REST next/error, WS events, awaited exports, promise `finally`). The full
  rule and reference files are in [ui-architecture.md](ui-architecture.md).
- `ApiService` reads `environment.apiBaseUrl` / `environment.wsBaseUrl`; only the
  ports (`8020`) are fixed, the hostname is resolved at runtime so localhost and
  LAN access both work.
- Design tokens and typography follow the Nothing Design System (see the XWA
  design skill): self-hosted fonts, no shadows/gradients/skeletons, ALL CAPS
  Space Mono labels and the `--gold` token for export hover states.

## Data contracts

REST errors use the xwa-sdk `Error` envelope. Live stream events conform to the
xwa-sdk `Event` schema (`seq`, `type`, `tool`, `analysis_id`, `ts`, `payload`).
The backend consumes the `xwa-sdk` Python package installed local-first by
`musha.sh` (editable sibling repo) with the git fallback documented in
`requirements.txt`.

## Roadmap decision: data-leakage channels

`ROADMAP.md` previously marked "Detect data-leakage channels (postMessage,
beacons)" as done, but no such detector exists. The item is back to `[ ]`.
The current analyzer is a passive HTML inventory; active channel detection
(postMessage listeners, `navigator.sendBeacon`, pixel beacons) requires script
analysis/DOM instrumentation and is tracked as future work.
