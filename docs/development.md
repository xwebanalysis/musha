# Development

## Requirements

| Component | Requirement |
|-----------|-------------|
| Node.js | >= 24.15 (Angular 22 CLI minimum) |
| Python | >= 3.10 (locally); the Docker image uses 3.13 |
| Docker | optional — only for the compose mode |
| Database | none for native mode (SQLite); PostgreSQL for compose mode |

## Execution modes

`musha.sh` is the entry point:

| Command | Description |
|---------|-------------|
| `./musha.sh docker all` | Full stack: frontend, backend, PostgreSQL |
| `./musha.sh docker backend` | Backend plus its `depends_on` service (PostgreSQL) |
| `./musha.sh docker frontend` | Frontend only |
| `./musha.sh local backend` | Native backend on :8000 with SQLite |
| `./musha.sh local frontend` | Native frontend on :4200 |
| `./musha.sh local all` | Both processes (backend in background) |

Manual equivalents:

```bash
# backend (native, SQLite)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DB_DRIVER=sqlite
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# frontend (native)
cd frontend
npm install
npm start
```

## Environment variables (backend)

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_DRIVER` | `postgresql` | `postgresql` or `sqlite` |
| `DB_PATH` | `./musha.db` | SQLite database file (used when `DB_DRIVER=sqlite`) |
| `DB_HOST` | `db` | PostgreSQL host |
| `DB_NAME` | `musha` | PostgreSQL database name |
| `DB_USER` | `postgres` | PostgreSQL user |
| `DB_PASS` | `postgres` | PostgreSQL password |

## Verification

### Backend

```bash
curl http://localhost:8000/api/health
curl -X POST http://localhost:8000/api/content/inventory \
  -H 'Content-Type: application/json' \
  -d '{"target":"https://en.wikipedia.org"}'
```

### Tests

```bash
cd backend
python -m pytest tests -q
```

### Frontend

```bash
cd frontend
npm run build        # production build into dist/
```

Open http://localhost:4200, wait for the backend badge to show "backend online", enter a target and run Analyze.

## Cleanup

```bash
./clean.sh
```

Stops compose services (with volumes), removes the local venv, the SQLite file, `node_modules` and `dist`.

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| Frontend shows "backend offline" | Backend not running — run backend first; CORS is open in development |
| `502` on inventory | Target unreachable (DNS, TLS, non-2xx). Check `error_message` in the response |
| Angular CLI version mismatch | Node below 24.15 — use a version manager (e.g. `fnm use 24`) |
| `xwa-sdk` install fails | The backend dependency is fetched from the XWA SDK git repository; network access to GitHub is required |
