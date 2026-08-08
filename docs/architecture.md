# Architecture

## Overview

Musha is a two-tier web application: an Angular single-page application and a FastAPI service. The backend owns the analysis pipeline and persistence; the frontend renders the inventory.

## Backend

Layout:

```
backend/
├── app/
│   ├── __init__.py
│   ├── analyzer.py      # resource extraction and provider fingerprinting
│   ├── database.py      # engine setup, SQLite/PostgreSQL switch
│   ├── main.py          # FastAPI app, REST routes, WebSocket endpoint
│   ├── models.py        # SQLAlchemy ORM models
│   └── schemas.py       # Pydantic v2 request/response models
├── tests/               # parser unit tests (no network)
├── Dockerfile           # python:3.13-slim
└── requirements.txt
```

### Components

- **analyzer.py** — the analysis core:
  - `inventory_resources(html, page_url)` — extracts `<script src>`, `<iframe src>`, stylesheet and preconnect `<link>` elements. Relative and protocol-relative URLs are resolved against the page URL; `data:`/`blob:`/`about:` URLs are skipped; duplicates are removed.
  - Captures `integrity` (SRI), `crossorigin`, `async` and `defer` attributes.
  - `fingerprint(url)` — matches the URL against a provider rule table (~45 rules) returning `(provider, category)`.
- **models.py** — two tables: `content_analyses` (the analysis session) and `third_party_resources` (one row per resource with type, URL, host, attributes, provider and category).
- **database.py** — SQLite (`DB_DRIVER=sqlite`) or PostgreSQL switch, WAL + foreign keys for SQLite.
- **main.py** — REST route `POST /api/content/inventory`, health check, WebSocket `WS /api/content/live` streaming xwa-sdk `Event` envelopes (`analysis_started`, `analysis_progress`, one `item_found` per resource, `analysis_completed`/`analysis_error`).

### Analysis flow

1. The client calls `POST /api/content/inventory` with a target.
2. A `ContentAnalysis` row is created with status `RUNNING`.
3. The page is fetched (redirects followed), the title captured, and resources are extracted and fingerprinted.
4. Resources are persisted and linked to the analysis; status becomes `COMPLETED` (or `ERROR`).

## Frontend

Layout:

```
frontend/
├── src/
│   ├── app/
│   │   ├── app.config.ts       # providers (router, HttpClient)
│   │   ├── app.routes.ts
│   │   ├── app.ts              # dashboard component
│   │   ├── app.html            # target form, resource tables, export
│   │   ├── app.scss            # Nothing Design System styles
│   │   └── services/
│   │       ├── api.service.ts  # typed REST client
│   │       └── theme.service.ts# dark/light mode with Angular Signals
│   └── index.html
├── Dockerfile                  # node:24
├── nginx.conf                  # SPA fallback for production serving
└── package.json                # Angular 22.1
```

- The dashboard shows backend health, runs the inventory and renders three tables (scripts, stylesheets, iframes) with provider, URL and attribute columns.
- `ApiService` targets `http://<current hostname>:8000`.
- Design tokens and typography follow the Nothing Design System (see the XWA design skill); export buttons use the gold hover convention.

## Data contracts

Live stream events conform to the xwa-sdk `Event` schema. The backend consumes the `xwa-sdk` Python package installed from the XWA SDK repository.
