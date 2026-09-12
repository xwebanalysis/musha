# API Reference

Base URL (local): `http://localhost:8020`. OpenAPI/Swagger UI: `http://localhost:8020/docs`.

## Conventions

- Responses use JSON. Timestamps in events are UTC ISO-8601 (`+00:00`).
- Errors follow the xwa-sdk `Error` envelope:

```json
{
  "error": {
    "code": "UPSTREAM_ERROR",
    "message": "Failed to fetch target: ...",
    "detail": null,
    "retryable": true
  }
}
```

| Status | Code | Condition |
|--------|------|-----------|
| `401` | `UNAUTHORIZED` | Bearer token missing/invalid (only when auth is enabled) |
| `404` | `NOT_FOUND` | Analysis does not exist |
| `422` | `VALIDATION_ERROR` | Request/query validation failed |
| `429` | `RATE_LIMITED` | Rate limit exceeded (default 120 req/min per IP; `/api/health` exempt) |
| `502` | `UPSTREAM_ERROR` | Target fetch failed (DNS, TLS, non-2xx) |
| `503` | `SERVICE_UNAVAILABLE` | Database not reachable (`/api/health`) |

CORS is configurable through `XWA_CORS_ORIGINS` (comma-separated origins); when
unset, localhost and private LAN ranges are allowed. Credentials are disabled —
use `Authorization: Bearer`.

## REST

### GET /

Service information.

```json
{ "status": "ok", "service": "musha", "version": "0.2.0" }
```

### GET /api/health

Health check including real database connectivity. Returns `200` when the
database answers and `503` otherwise (the `status` and `database` fields both
become `"error"`).

```json
{ "status": "ok", "database": "ok", "version": "0.2.0", "tool": "musha" }
```

### POST /api/content/inventory

Runs the resource inventory on a target and persists the results.

Request:

```json
{ "target": "https://example.com" }
```

- `target` — domain or full URL. A missing scheme is completed with `https://`.

Response `200 OK`:

```json
{
  "analysis": {
    "id": 1,
    "target": "https://example.com",
    "status": "COMPLETED",
    "analysis_type": "content_scan",
    "created_at": "2026-08-08T10:00:00Z",
    "started_at": "2026-08-08T10:00:00Z",
    "finished_at": "2026-08-08T10:00:02Z",
    "error_message": null,
    "page_title": "Example",
    "resources": [
      {
        "id": 1,
        "resource_type": "script",
        "url": "https://www.googletagmanager.com/gtag/js?id=G-XXX",
        "host": "www.googletagmanager.com",
        "integrity": null,
        "crossorigin": null,
        "async_attr": true,
        "defer_attr": false,
        "provider": "Google Tag Manager",
        "category": "tag-manager"
      }
    ]
  },
  "resource_count": 1,
  "script_count": 1,
  "iframe_count": 0,
  "stylesheet_count": 0,
  "preconnect_count": 0
}
```

On fetch failure the analysis is stored with status `ERROR` and the request
returns `502` with the error envelope.

### GET /api/analyses

Lists the 50 most recent analyses (newest first).

```json
[
  {
    "id": 1,
    "target": "https://example.com",
    "status": "COMPLETED",
    "analysis_type": "content_scan",
    "created_at": "2026-08-08T10:00:00Z",
    "page_title": "Example",
    "resource_count": 1,
    "script_count": 1,
    "iframe_count": 0,
    "stylesheet_count": 0,
    "preconnect_count": 0
  }
]
```

### GET /api/analyses/{id}

Full analysis detail including the resource list. `404` when not found.

### GET /api/analyses/{id}/export?format=json|csv

Downloadable export with `Content-Disposition: attachment`:

- `format=json` (default) — same shape as the persisted analysis; `musha-analysis-<id>.json`.
- `format=csv` — one row per resource; `musha-analysis-<id>.csv`.

Any other `format` value returns `422`. `404` when not found.

### DELETE /api/analyses/{id}

Deletes one analysis and its resources. Returns `204`; `404` when not found.

### DELETE /api/analyses

Deletes all analyses and their resources. Returns `204`.

### POST /api/auth/token

Issues a signed JWT (HS256). Only available when `MUSHA_JWT_SECRET` is set;
returns `403` when auth is disabled.

Request:

```json
{ "password": "..." }
```

Response `200 OK`:

```json
{ "token": "<jwt>", "expires_in": 86400 }
```

## WebSocket

### WS /api/content/live?target=...

Persists the analysis and streams inventory progress. Query parameters:
`target` (required) and `token` (required only when `MUSHA_JWT_SECRET` is set —
WebSocket clients cannot send headers).

Every message is an xwa-sdk `Event` envelope. `analysis_id` is the **persisted
analysis id serialized as a string** (never the target), `seq` starts at 1 and
is monotonic, and `ts` is UTC ISO-8601.

```json
{
  "seq": 1,
  "type": "analysis_started",
  "tool": "musha",
  "analysis_id": "42",
  "ts": "2026-08-08T10:00:00.123456+00:00",
  "payload": { "target": "https://example.com" }
}
```

| seq order | type | payload |
|-----------|------|---------|
| 1 | `analysis_started` | `{ "target": ... }` |
| 2 | `analysis_progress` | `{ "page": <final URL>, "title": <page title> }` |
| 3..n | `item_found` | one per resource: `{ "kind": <type>, "url": ..., "provider": ... }` |
| n+1 | `analysis_completed` | `{ "resource_count": ..., "script_count": ..., "iframe_count": ..., "stylesheet_count": ..., "preconnect_count": ... }` |

On fetch failure the analysis is marked `ERROR`, a terminal `analysis_error`
event is sent with the xwa-sdk `Error` shape
(`{ "code": "TARGET_ERROR", "message": ..., "retryable": true }`), and the
connection closes. If the client disconnects mid-run the analysis is marked
`CANCELLED`.

## Authentication and rate limiting

- When `MUSHA_JWT_SECRET` is set, every `/api/*` route except `/`, `/api/health`
  and `/api/auth/token` requires `Authorization: Bearer <token>` (HS256, 24 h).
  When unset (default) the API is open.
- All non-exempt routes share an in-memory sliding window:
  `MUSHA_RATE_LIMIT_MAX` requests per client IP per 60 s (default `120`).

## Frontend consumption

The Angular UI (port `4220`) uses these endpoints as follows:

- `/api/health` — sidebar `BACKEND ONLINE` indicator on startup.
- `POST /api/content/inventory` — **ANALYZE** button (synchronous fallback).
- `WS /api/content/live` — **LIVE STREAM** button; frames are validated by
  `parseLiveEvent()` in `core/live.service.ts` and rendered in the terminal and
  phase row. On `analysis_completed` the UI fetches the persisted analysis with
  `GET /api/analyses/{id}` and renders the detail tables.
- `GET /api/analyses` — history list and exports console.
- `GET /api/analyses/{id}/export?format=json|csv` — `SERVER` links in the
  export actions; additionally the client builds JSON/CSV/PDF files locally with
  `core/export.service.ts` (PDF via lazily imported jsPDF).
- `DELETE /api/analyses/{id}` and `DELETE /api/analyses` — history actions.
