# Musha Documentation

Documentation for the Musha web content and DOM analysis module.

| Document | Description |
|----------|-------------|
| [architecture.md](architecture.md) | Stack, project layout and data flow |
| [ui-architecture.md](ui-architecture.md) | Frontend UI rules, zoneless change detection, testing |
| [api.md](api.md) | REST and WebSocket API reference |
| [development.md](development.md) | Running, environment variables and verification |

## Quick orientation

- Musha is a self-contained web application: an Angular 22 frontend (:4220) and a FastAPI backend (:8020).
- Local mode is the default and uses SQLite; PostgreSQL is only used by the docker mode.
- The analysis pipeline extracts third-party resources from a target page and fingerprints their providers.
- Live stream events use the xwa-sdk `Event` envelope with the persisted `analysis_id`; REST errors use the xwa-sdk `Error` envelope.
- The UI follows the Nothing Design System shared across XWA modules (dark instrument panel + light mode).

## Quick start

```bash
./musha.sh local all      # native run (SQLite): backend :8020 + frontend :4220
./musha.sh docker all     # full stack with PostgreSQL 17
```

See [development.md](development.md) for all execution modes and
[api.md](api.md) for the endpoint reference.
