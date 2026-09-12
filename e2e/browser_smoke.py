#!/usr/bin/env python3
"""Real-browser smoke test for Musha (zoneless change-detection guard).

The app is Angular 22 zoneless: every async callback that mutates component
state must call ``ChangeDetectorRef.markForCheck()`` or the view stalls on
"[ LOADING... ]" until the user interacts. This script drives the real UI in
Chromium and asserts that data renders *without any extra interaction* after
each async operation (REST inventory, live WebSocket inventory, history,
detail deep-links, exports and locale toggle).

Stack expected while running (see e2e/README.md):
  frontend  http://localhost:4220
  backend   http://localhost:8020
  fixture   http://localhost:8103   (third-party script/iframe/CSS/preconnect)

Usage:
  /home/x/Documents/xwebanalysis/samurai/backend/.venv/bin/python \
      e2e/browser_smoke.py

Environment overrides: MUSHA_FRONTEND_URL, MUSHA_BACKEND_URL,
MUSHA_FIXTURE_URL.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request

from playwright.sync_api import Page, sync_playwright

FRONTEND = os.environ.get("MUSHA_FRONTEND_URL", "http://localhost:4220")
BACKEND = os.environ.get("MUSHA_BACKEND_URL", "http://localhost:8020")
FIXTURE = os.environ.get("MUSHA_FIXTURE_URL", "http://localhost:8103")

results: list[tuple[bool, str, str]] = []
console_errors: list[str] = []
page_errors: list[str] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    results.append((ok, label, detail))
    suffix = f" — {detail}" if detail else ""
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}{suffix}", flush=True)


def wait_health(url: str, timeout: float = 45.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/api/health", timeout=3) as response:
                payload = json.load(response)
            if payload.get("status") == "ok":
                return
        except Exception as exc:  # noqa: BLE001 - retry loop
            last_error = exc
        time.sleep(1)
    raise RuntimeError(f"backend not healthy at {url}: {last_error}")


def api_json(url: str) -> object:
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.load(response)


def analyzer_target(page: Page, target: str, button: str) -> None:
    page.goto(FRONTEND)
    page.wait_for_selector("#target-input")
    page.fill("#target-input", target)
    page.get_by_role("button", name=button).click()


def run() -> int:
    wait_health(BACKEND)
    print(f"[+] Musha backend healthy at {BACKEND}", flush=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.set_default_timeout(30_000)
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.on("pageerror", lambda error: page_errors.append(str(error)))

        try:
            # ── REST inventory from the UI ───────────────────────────────────
            print("[*] analyzer: REST inventory", flush=True)
            analyzer_target(page, FIXTURE, "ANALYZE")
            page.wait_for_selector("app-analysis-detail .detail", timeout=60_000)
            rest_metrics = page.locator("app-analysis-detail .metric-value").all_inner_texts()
            rest_rows = page.locator("app-analysis-detail app-detail-table tbody tr").count()
            detail_text = page.locator("app-analysis-detail .detail").inner_text()
            check(
                len(rest_metrics) >= 4
                and sum(int(value) for value in rest_metrics[:4]) >= 7
                and int(rest_metrics[0]) >= 3,
                "analyzer REST: metric cards rendered",
                "scripts/styles/iframes/preconnects=" + "/".join(rest_metrics[:4]),
            )
            check(rest_rows >= 3, "analyzer REST: resource tables rendered", f"{rest_rows} rows")
            check(
                "Google Analytics" in detail_text and "jsDelivr" in detail_text,
                "analyzer REST: providers classified",
                "Google Analytics + jsDelivr",
            )

            # ── Live WebSocket inventory from the UI ─────────────────────────
            print("[*] analyzer: live WS inventory", flush=True)
            analyzer_target(page, FIXTURE, "LIVE STREAM")
            page.wait_for_selector("app-analysis-detail .detail", state="detached", timeout=15_000)
            page.wait_for_selector("app-analysis-detail .detail", timeout=90_000)
            live_rows = page.locator("app-analysis-detail app-detail-table tbody tr").count()
            phase_text = re.sub(r"\s+", " ", page.locator(".phase-row").inner_text())
            check(bool(phase_text.strip()), "analyzer live: phase row rendered", phase_text[:90])
            check(live_rows >= 3, "analyzer live: detail rendered after WS", f"{live_rows} rows")

            # ── History list on entry (no clicks) ────────────────────────────
            print("[*] history: list on entry", flush=True)
            page.goto(f"{FRONTEND}/history")
            page.wait_for_selector(".history-item")
            items = page.locator(".history-item").count()
            first_item = re.sub(
                r"\s+", " ", page.locator(".history-item").first.inner_text()
            )
            check(items >= 2, "history: rows rendered without clicks", f"{items} rows")
            check(
                "localhost:8103" in first_item,
                "history: row shows fixture target",
                first_item[:110],
            )

            analyses = api_json(f"{BACKEND}/api/analyses")
            assert isinstance(analyses, list) and analyses, "backend returned no analyses"
            analysis_id = int(analyses[0]["id"])
            print(f"    backend analyses={len(analyses)} latest id={analysis_id}", flush=True)

            # ── Detail by direct URL ─────────────────────────────────────────
            print("[*] detail: direct URL", flush=True)
            page.goto(f"{FRONTEND}/history/{analysis_id}")
            page.wait_for_selector(".detail", timeout=30_000)
            page.wait_for_function(
                "document.querySelectorAll('app-detail-table tbody tr').length >= 3",
                timeout=30_000,
            )
            hero = page.locator(".hero-number").inner_text()
            detail_rows = page.locator("app-detail-table tbody tr").count()
            check(hero.strip().isdigit() and int(hero) >= 7, "detail: hero resource count", hero)
            check(detail_rows >= 3, "detail: direct URL tables rendered", f"{detail_rows} rows")

            # ── Exports page: client JSON/PDF downloads + server links ───────
            print("[*] exports: downloads", flush=True)
            page.goto(f"{FRONTEND}/exports")
            page.wait_for_selector(".exports-target")
            export_rows = page.locator("tbody tr").count()
            check(export_rows >= 2, "exports: table rows rendered", f"{export_rows} rows")

            server_json = page.get_by_role("link", name="SERVER JSON").first.get_attribute("href")
            server_csv = page.get_by_role("link", name="SERVER CSV").first.get_attribute("href")
            check(
                bool(server_json) and "format=json" in server_json,
                "exports: server JSON href",
                server_json or "",
            )
            check(
                bool(server_csv) and "format=csv" in server_csv,
                "exports: server CSV href",
                server_csv or "",
            )

            with page.expect_download(timeout=60_000) as json_download:
                page.get_by_role("button", name="CLIENT JSON").first.click()
            json_name = json_download.value.suggested_filename
            check(json_name.endswith(".json"), "exports: client JSON download", json_name)
            page.wait_for_function(
                "document.querySelector('main .text-success')?.textContent?.includes('DOWNLOADED')",
                timeout=30_000,
            )
            notice = page.locator("main .text-success").first.inner_text()
            check("DOWNLOADED" in notice and "JSON" in notice, "exports: JSON notice", notice)

            with page.expect_download(timeout=90_000) as pdf_download:
                page.get_by_role("button", name="CLIENT PDF").first.click()
            pdf_name = pdf_download.value.suggested_filename
            check(pdf_name.endswith(".pdf"), "exports: client PDF download", pdf_name)
            page.wait_for_function(
                "document.querySelector('main .text-success')?.textContent?.includes('PDF')",
                timeout=30_000,
            )
            pdf_button_enabled = page.get_by_role("button", name="CLIENT PDF").first.is_enabled()
            check(pdf_button_enabled, "exports: busy state released after PDF")

            # ── Locale toggle keeps the data ─────────────────────────────────
            print("[*] locale toggle keeps data", flush=True)
            page.locator(".side-btn").first.click()
            page.wait_for_function(
                "document.querySelector('.nav-link:nth-child(2)')?.textContent?.includes('HISTORIAL')",
                timeout=15_000,
            )
            toggled_rows = page.locator("tbody tr").count()
            toggled_target = page.locator(".exports-target").first.inner_text()
            check(
                toggled_rows == export_rows and "localhost:8103" in toggled_target,
                "locale ES: table keeps the same data",
                f"{toggled_rows} rows, target={toggled_target}",
            )
        finally:
            context.close()
            browser.close()

    print(f"[*] console errors: {len(console_errors)}", flush=True)
    for message in console_errors:
        print(f"    CONSOLE ERROR: {message}", flush=True)
    print(f"[*] page errors: {len(page_errors)}", flush=True)
    for message in page_errors:
        print(f"    PAGE ERROR: {message}", flush=True)

    check(not console_errors, "no console errors")
    check(not page_errors, "no page errors")

    failed = [label for ok, label, _ in results if not ok]
    print(f"\n{'PASS' if not failed else 'FAIL'}: {len(results) - len(failed)}/{len(results)} checks")
    for label in failed:
        print(f"  - {label}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
