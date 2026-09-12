# Musha — Browser E2E smoke (`browser_smoke.py`)

Real-Chromium regression guard for the Angular 22 **zoneless** change-detection
contract (see `docs/ui-architecture.md`). It drives the actual UI and asserts
that async data renders **without any extra user interaction** after each
operation — the exact failure mode of a missing `ChangeDetectorRef.markForCheck()`.

## What it covers

| Area | Assertions |
|------|------------|
| Analyzer REST | ANALYZE against the fixture; metric cards (3 scripts / 1 CSS / 1 iframe / 2 preconnects), tables, provider classification (Google Analytics + jsDelivr) |
| Analyzer live WS | LIVE STREAM; phase row renders, detail tables render after `analysis_completed` |
| History | Rows visible on entry (no click), first row shows the fixture target |
| Detail deep link | `/history/<id>` renders hero count + resource tables |
| Exports | Server JSON/CSV hrefs, client JSON + PDF downloads, notice text, busy state released after PDF |
| Locale | EN→ES toggle keeps the same rows/target while labels translate |
| Console | No `console.error` and no `pageerror` for the whole run |

## Prerequisites

* Backend venv with Playwright (used for the script):
  `/home/x/Documents/xwebanalysis/samurai/backend/.venv/bin/python`
  (Playwright 1.62 + Chromium already installed).
* Musha stack running locally (`./musha.sh local`): frontend `:4220`,
  backend `:8020`.
* Fixture server on `:8103` with third-party resources. The fixture source
  lives in `e2e/fixtures/`; serve it from `/tmp/opencode/fixture-mus`:

```bash
mkdir -p /tmp/opencode/fixture-mus
cp -r e2e/fixtures/. /tmp/opencode/fixture-mus/
python3 -m http.server 8103 --directory /tmp/opencode/fixture-mus &
```

The fixture `index.html` contains a stylesheet + script to
`cdn.jsdelivr.net`, scripts to `googletagmanager.com` and
`google-analytics.com`, preconnects to `fonts.googleapis.com` /
`fonts.gstatic.com` and an iframe to `youtube.com` (7 resources total).

## Run

```bash
cd /home/x/Documents/xwebanalysis/musha
/home/x/Documents/xwebanalysis/samurai/backend/.venv/bin/python e2e/browser_smoke.py
```

Environment overrides: `MUSHA_FRONTEND_URL`, `MUSHA_BACKEND_URL`,
`MUSHA_FIXTURE_URL`. Exit code is non-zero if any check fails.

Expected tail:

```
PASS: 19/19 checks
```

## Notes

* The script performs no interaction while waiting for async state; only the
  initial form fill/click. That is deliberate: it reproduces the user-visible
  zoneless bug (`[ LOADING... ]` stuck / empty tables).
* Export download names are asserted (`musha-analysis-<id>.json|pdf`) and the
  PDF button must be enabled again afterwards, which covers the async
  `finally` block in both `exports.ts` and `shared/export-actions`.
