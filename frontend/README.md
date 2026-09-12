# Musha frontend

Angular 22 (standalone, zoneless, Vitest) frontend for the Musha module.

## Development server

```bash
npm start          # ng serve --host 0.0.0.0, port 4220 (angular.json)
```

Open `http://localhost:4220/`. The backend is expected on port `8020`; the host
is resolved at runtime in `src/environments/environment.ts`.

## Unit tests

```bash
npm test -- --run  # single run (wrapper maps --run onto the Angular builder)
```

## Build

```bash
npm run build      # artifacts in dist/frontend
```

See `../README.md` and `../docs/development.md` for the full local workflow.
