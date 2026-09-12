# Musha Development Roadmap

This document tracks the strategic steps required to evolve the Musha application into a full-scale web content and DOM analysis module.
This file is formatted to be synced automatically with GitHub Issues using the `xgh` roadmap standard.

## Infrastructure & Core Initialization <!-- phase:infrastructure -->

- [x] Scaffold backend and frontend project structure
- [x] Dockerize environments with local development HMR support
- [x] Configure Docker-compose for rapid local development
- [x] Define shared snapshot data model aligned with xwa-sdk
- [x] Local-first mode: SQLite + uv venv + xwa-sdk editable install (`./musha.sh local`)

## Third-Party Inventory <!-- phase:third-party -->

- [x] Extract scripts, iframes, and external resource URLs
- [x] Fingerprint third-party providers and trackers
- [ ] Detect data-leakage channels (postMessage, beacons) — not implemented; the current analyzer is a passive HTML inventory (see docs/architecture.md)
- [ ] Build vendor classification database

## Structural Diffing <!-- phase:structural-diff -->

- [ ] Build DOM tree normalization pipeline
- [ ] Implement tree-based structural diff algorithm
- [ ] Classify changes (added, removed, modified, moved)
- [ ] Ignore volatile nodes (timestamps, session tokens, nonces)

## Content Drift Detection <!-- phase:content-drift -->

- [ ] Capture and store page snapshots over time
- [ ] Implement semantic text drift analysis
- [ ] Detect price, availability, and layout changes
- [ ] Generate drift alerts with severity scoring

## Reporting & Production Hardening <!-- phase:production-hardening -->

- [ ] Build content analysis report generator
- [x] Create JSON/CSV export for analysis results (server-side, `Content-Disposition`)
- [x] Persisted history API: `GET /api/analyses`, detail, delete one/all
- [x] Wrap backend routes with JWT Authentication middleware (optional via `MUSHA_JWT_SECRET`)
- [x] Implement rate limiting and access controls (`MUSHA_RATE_LIMIT_MAX`, `/api/health` exempt)
- [x] Correct xwa-sdk `Event.analysis_id` (persisted id), `seq` and UTC `ts`

## Frontend <!-- phase:frontend -->

- [x] Restructure to `core/` (api, live WS, theme, i18n, export) + `shared/` (terminal, metric-card, status-badge, export-actions, detail-table)
- [x] Lazy router with sidebar navigation: analyzer, history list/detail, exports console
- [x] Consume `/api/content/live` xwa-sdk `Event` stream (progress + terminal); `POST /api/content/inventory` kept as fallback
- [x] Server-side export links + client JSON/CSV/PDF (jsPDF lazy chunk)
- [x] Nothing tokens with `--gold` (no hardcoded `#FFD700`), self-hosted fonts, no Google Fonts at runtime
- [x] Vitest suite: ApiService, `parseLiveEvent()`, CSV builder, analyzer component, app shell
