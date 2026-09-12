# Development

## Requirements

| Component | Requirement |
|-----------|-------------|
| Node.js | >= 24.15 (Angular 22 CLI minimum) |
| Python | 3.13 (managed with `uv`); the Docker image uses 3.13 |
| uv | `~/.local/bin/uv` (used to create the venv and install packages) |
| Docker | optional — only for the compose mode |
| Database | none for local mode (SQLite); PostgreSQL 17 for docker mode |

## Execution modes

`musha.sh` is the entry point. `local` is the default:

| Command | Description |
|---------|-------------|
| `./musha.sh` | Same as `./musha.sh local all` |
| `./musha.sh local all` | Native backend :8020 (SQLite) + frontend :4220 |
| `./musha.sh local backend` | Backend only, foreground |
| `./musha.sh local frontend` | Frontend only |
| `./musha.sh docker all` | Full stack on :4220/:8020 plus PostgreSQL 17 on :5442 |
| `./musha.sh docker backend` | Backend plus its `depends_on` service (PostgreSQL) |
| `./musha.sh docker frontend` | Frontend only |

Legacy aliases `--sqlite`, `--native` and `--fast` are accepted as `local`.

The `local` mode:

1. Creates/updates `backend/.venv` with `uv venv --python 3.13 --seed`.
2. Installs `requirements-dev.txt` (runtime + pytest/anyio).
3. Installs the sibling `xwa-sdk` binding in editable mode when
   `/home/x/Documents/xwebanalysis/xwa-sdk/bindings/python` exists; otherwise
   falls back to the git spec documented in `requirements.txt`.
4. Starts uvicorn on :8020 with `DB_DRIVER=sqlite`, waits for `/api/health`,
   then starts Angular on :4220.

Manual equivalents:

```bash
# backend (native, SQLite)
cd backend
~/.local/bin/uv venv --python 3.13 --seed .venv
~/.local/bin/uv pip install --python .venv/bin/python -r requirements-dev.txt
~/.local/bin/uv pip install --python .venv/bin/python -e ../../xwa-sdk/bindings/python
export DB_DRIVER=sqlite DB_PATH=./musha.db
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8020 --reload

# frontend (native)
cd frontend
npm ci
npm start                        # ng serve --host 0.0.0.0, port 4220 (angular.json)
```

## Environment variables (backend)

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_DRIVER` | `sqlite` | `sqlite` or `postgresql` |
| `DB_PATH` | `./musha.db` | SQLite database file (used when `DB_DRIVER=sqlite`) |
| `DB_HOST` | `db` | PostgreSQL host |
| `DB_NAME` | `musha` | PostgreSQL database name |
| `DB_USER` | `postgres` | PostgreSQL user |
| `DB_PASS` | `postgres` | PostgreSQL password |
| `XWA_CORS_ORIGINS` | unset | Comma-separated allowed origins; unset = localhost + LAN regex |
| `MUSHA_JWT_SECRET` | unset | When set, all `/api/*` routes require an HS256 Bearer token |
| `MUSHA_AUTH_PASSWORD` | `musha` | Password accepted by `POST /api/auth/token` |
| `MUSHA_RATE_LIMIT_MAX` | `120` | Requests per client IP per 60 s window (`XWA_RATE_LIMIT_MAX` also accepted) |

`musha.sh` also honors `MUSHA_BACKEND_PORT`, `MUSHA_FRONTEND_PORT`, `MUSHA_DB_PATH` and `XWA_SDK_DIR`.

Example with auth enabled:

```bash
export MUSHA_JWT_SECRET=change-me-to-at-least-32-bytes
export MUSHA_AUTH_PASSWORD=change-me
./musha.sh local backend
# obtain a token:
curl -X POST http://localhost:8020/api/auth/token \
  -H 'Content-Type: application/json' -d '{"password":"change-me"}'
# use it:
curl -H 'Authorization: Bearer <token>' http://localhost:8020/api/analyses
# WebSocket (token in the query string):
#   ws://localhost:8020/api/content/live?target=https://example.com&token=<token>
```

## Tests and verification

```bash
# backend tests (isolated SQLite temp DB, no network)
cd backend
.venv/bin/python -m pytest -q

# smoke test
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8020 &
curl -s http://localhost:8020/api/health
curl -s -X POST http://localhost:8020/api/content/inventory \
  -H 'Content-Type: application/json' -d '{"target":"https://example.com"}'
curl -s http://localhost:8020/api/analyses
curl -sD - -o /dev/null "http://localhost:8020/api/analyses/1/export?format=csv"

# frontend
cd frontend
npm ci
npm test -- --run        # vitest via the Angular builder
npm run build
npm audit --omit=dev     # must report 0 vulnerabilities
```

The frontend test suite covers the typed `ApiService` (REST + URL builders), the
`parseLiveEvent()` xwa-sdk envelope parser, the client CSV export builder, the
analyzer component (REST fallback + live WS events) and the app shell/router.

The UI is served with self-hosted fonts from `public/fonts` (`src/_fonts.scss`);
`index.html` loads no external font providers. jsPDF is only fetched when a PDF
export is requested (lazy chunk), so the initial bundle stays lean.

## Cleanup

```bash
./clean.sh
```

Stops compose services (with volumes) and removes the venv, the SQLite file
(plus `-wal`/`-shm`), `node_modules`, `dist`, `.angular` and caches.

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| Frontend shows "backend offline" | Backend not running on :8020, or the browser origin is not allowed — use `XWA_CORS_ORIGINS` |
| `502` on inventory | Target unreachable (DNS, TLS, non-2xx). Check `error_message` in the response |
| `429` on repeated requests | Rate limit hit (`MUSHA_RATE_LIMIT_MAX`, default 120/min) |
| Angular CLI version mismatch | Node below 24.15 — `musha.sh` prepends the mise Node 24 directory |
| `xwa-sdk` install fails | Sibling repo missing and no network access to GitHub — see `requirements.txt` for both options |
