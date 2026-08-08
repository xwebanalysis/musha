# Musha Documentation

Documentation for the Musha web content and DOM analysis module.

| Document | Description |
|----------|-------------|
| [architecture.md](architecture.md) | Stack, project layout and data flow |
| [api.md](api.md) | REST and WebSocket API reference |
| [development.md](development.md) | Running, environment variables and verification |

## Quick orientation

- Musha is a self-contained web application: an Angular 22 frontend and a FastAPI backend.
- The backend can run with PostgreSQL (Docker Compose) or SQLite (native mode).
- The analysis pipeline extracts third-party resources from a target page and fingerprints their providers.
- Live stream events use the xwa-sdk `Event` envelope, the shared data contract of the XWA ecosystem.
- The UI follows the Nothing Design System shared across XWA modules (dark instrument panel + light mode).

## Quick start

```bash
./musha.sh docker all     # full stack on localhost:4200 / localhost:8000
./musha.sh local all      # native run (SQLite), two processes
```

See [development.md](development.md) for all execution modes.
