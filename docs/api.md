# API Reference

Base URL (local): `http://localhost:8000`. OpenAPI/Swagger UI: `http://localhost:8000/docs`.

## REST

### GET /

Service information.

```json
{
  "status": "ok",
  "service": "musha",
  "version": "0.1.0"
}
```

### GET /api/health

Health check including database connectivity.

```json
{
  "status": "ok",
  "database": "ok",
  "version": "0.1.0"
}
```

### POST /api/content/inventory

Runs the third-party resource inventory on a target and persists the results.

Request:

```json
{
  "target": "https://example.com"
}
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
  "stylesheet_count": 0
}
```

Errors:

| Status | Condition |
|--------|-----------|
| `422` | Missing or empty `target` (request validation) |
| `502` | The target could not be fetched — body carries `detail` |

## WebSocket

### WS /api/content/live?target=...

Streams inventory progress. Query parameter `target` is required.

| seq order | type | payload |
|-----------|------|---------|
| 1 | `analysis_started` | `{ "target": ... }` |
| 2 | `analysis_progress` | `{ "page": <final URL>, "title": <page title> }` |
| 3..n | `item_found` | one per resource: `{ "kind": <type>, "url": ..., "provider": ... }` |
| n+1 | `analysis_completed` | `{ "resource_count": <int> }` |

On fetch failure the terminal event is `analysis_error` with `{ "code": "TARGET_ERROR", "message": ... }`.
