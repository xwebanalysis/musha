# Musha Frontend — UI Architecture

Status: current as of the Angular 22 / Nothing Design consolidation (Phase 5).

## Stack

| Layer | Choice |
|-------|--------|
| Framework | Angular 22 (standalone components, signals, zoneless by default) |
| Build | `@angular/build:application` (esbuild) |
| Tests | `@angular/build:unit-test` + Vitest 4 (jsdom) |
| Language | TypeScript 6 (strict templates) |
| Node | 24 (mise-managed; Angular does not support Node 26) |
| Styling | SCSS + Nothing Design tokens (no CSS-in-JS, no shadows/gradients) |
| PDF | `jspdf` (lazy-loaded) |

Ports follow the XWA convention: frontend `4220`, backend `8020`
(`src/environments/environment.ts`; the host is resolved at runtime).

## Directory layout

```
frontend/
├── public/fonts/                # self-hosted woff2 (Doto, Space Grotesk, Space Mono)
├── scripts/test.sh              # npm test wrapper (`--run` accepted and ignored)
├── e2e/                         # real-browser smoke (Playwright) + fixture (:8103)
│   ├── browser_smoke.py
│   └── fixtures/                # index.html with third-party resources
└── src/
    ├── _fonts.scss              # @font-face declarations (imported by styles.scss)
    ├── styles.scss              # Nothing Design tokens + typography utilities
    ├── index.html               # no Google Fonts at runtime
    └── app/
        ├── app.ts/html/scss     # shell: sidebar nav, backend health, theme/locale toggles
        ├── app.config.ts        # provideRouter, provideHttpClient, global error listeners
        ├── app.routes.ts        # lazy `loadComponent` routes per feature
        ├── core/                # singleton, framework-level concerns
        │   ├── api.service.ts   # typed REST/WS client (all HTTP goes through here)
        │   ├── live.service.ts  # WebSocket Observable + parseLiveEvent()
        │   ├── export.service.ts# client exports: JSON/CSV/PDF (jsPDF lazy)
        │   ├── i18n.service.ts  # en/es dictionaries (Angular signal)
        │   └── theme.service.ts # dark/light signal, `musha-theme` storage key
        ├── shared/              # reusable, presentation-only components
        │   ├── terminal/        # live log panel
        │   ├── metric-card/     # hero number + label (Doto)
        │   ├── status-badge/    # [ COMPLETED ] with status color
        │   ├── detail-table/    # generic flat data table
        │   └── export-actions/  # client JSON/CSV/PDF + server JSON/CSV
        └── features/            # one folder per route
            ├── analyzer/        # target input, REST + live WS runs, phases, terminal
            ├── history/         # list + detail deep link (`/history/:id`)
            └── exports/         # server/client export console
```

Rules:

- `core/` never imports from `features/`; `shared/` never injects state services.
- Every REST call is typed in `ApiService`; components never build URLs.
- WebSocket frames are parsed by `parseLiveEvent()` before reaching components.

## Runtime data flow

1. `ApiService` reads `environment.apiBaseUrl`/`wsBaseUrl` and exposes typed
   methods: `health`, `inventory`, `listAnalyses`, `getAnalysis`,
   `deleteAnalysis`, `deleteAllAnalyses`, `exportUrl`, `liveUrl`.
2. The analyzer runs either `POST /api/content/inventory` (REST fallback) or the
   `/api/content/live` WebSocket. Each live frame is `parseLiveEvent()`-d
   (malformed frames are ignored) and drives the phase row + terminal; on
   `analysis_completed` the persisted analysis is re-fetched with
   `getAnalysis()`. The history list/detail and the exports console read the
   same `ApiService`.
3. Zoneless change detection (app is Angular 22 **without zone.js**; there is no
   `polyfills` entry and no `provideZoneChangeDetection`). Any component that
   mutates plain properties inside an async callback **must** call
   `ChangeDetectorRef.markForCheck()` after every mutation; otherwise the view
   keeps the stale render until some unrelated user interaction happens
   (symptoms: `[ LOADING... ]` stuck, empty tables with data in the backend,
   values appearing only after a click). Rules:
   - inject `private readonly cdr = inject(ChangeDetectorRef);` in the component;
   - call `this.cdr.markForCheck()` in **both** `next` and `error` of every
     `HttpClient` subscription (and after awaited work, e.g. PDF export);
   - call it at the end of every WebSocket `onmessage`/event handler and in
     `finishLive()`-style follow-up subscriptions;
   - promise chains (`.finally()`) also run outside Angular: mark there too;
   - signals (theme, i18n locale) schedule their own updates and need nothing;
   - template event handlers run change detection themselves, so `markForCheck`
     is only needed for callback-driven mutations.
   Reference implementations: `features/analyzer/analyzer.ts`,
   `features/history/history.ts`, `features/history/detail.ts`,
   `features/exports/exports.ts`, `app.ts`,
   `shared/export-actions/export-actions.ts`.

## Nothing Design rules in this app

- Tokens live only in `src/styles.scss`; `--gold` is the only place the gold hex
  exists (hover/export accents).
- Fonts are self-hosted in `public/fonts`; `index.html` has no Google Fonts
  links.
- No shadows, no skeletons, no emoji, no zebra striping; labels are Space Mono
  ALL CAPS (`.t-label`), the display font (Doto) is reserved for hero metrics.
- The dot-matrix motif is the sanctioned background exception.
- Errors are inline bracket text (`[ERROR: ...]`), never toasts.

## i18n

`I18nService` holds `locale` (signal, persisted as `musha-locale`) and the en/es
dictionaries. Templates call `t('key')`; the sidebar locale button toggles
EN/ES. Data is component state, so toggling the locale must never reset lists —
covered by the browser smoke test.

## Exports

| Scope | Client-side | Server-side |
|-------|-------------|-------------|
| Analysis detail | JSON, CSV, PDF (lazy jsPDF) | — |
| Exports console | JSON, PDF (per row) | `GET /api/analyses/{id}/export?format=json|csv` |

`ExportService` owns the download plumbing (Blob → object URL → anchor);
`analysisToCsv()` is unit-tested. The PDF path is async: the component's
`finally` block must call `markForCheck()` so the busy button state resolves.

## Testing

`npm test` builds the app for the test target and runs Vitest once
(`scripts/test.sh` maps `--run` for suite consistency). Coverage:

- `core/api.service.spec.ts` — endpoints, query encoding, export/live URLs.
- `core/live.service.spec.ts` — frame parsing/validation.
- `core/export.service.spec.ts` — CSV builder.
- `features/analyzer/analyzer.spec.ts` — REST + live event flow.
- `app.spec.ts` — shell rendering and backend health.

Real-browser coverage lives in `e2e/browser_smoke.py` (Playwright): it runs
REST + live inventory against the fixture and asserts that metric cards, tables,
history rows, direct detail links, exports and the EN/ES toggle render **without
extra interaction**, with zero console/page errors. See `e2e/README.md`.

## Commands

```bash
export PATH="$HOME/.local/share/mise/installs/node/24/bin:$PATH"
npm ci
npm test
npm run build
npm start          # dev server on 0.0.0.0:4220

# Browser smoke (stack + fixture must be up, see e2e/README.md)
/home/x/Documents/xwebanalysis/samurai/backend/.venv/bin/python e2e/browser_smoke.py
```
