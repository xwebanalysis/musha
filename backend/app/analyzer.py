"""Analysis core — phase 1: third-party resource inventory of a page."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import httpx
from bs4 import BeautifulSoup

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


class TargetError(Exception):
    """Raised when the target cannot be fetched or parsed."""


PROVIDER_RULES: tuple[tuple[str, str, str], ...] = (
    # (domain fragment, provider, category)
    ("googletagmanager.com", "Google Tag Manager", "tag-manager"),
    ("google-analytics.com", "Google Analytics", "analytics"),
    ("analytics.google.com", "Google Analytics", "analytics"),
    ("googleapis.com/css", "Google Fonts", "fonts"),
    ("fonts.googleapis.com", "Google Fonts", "fonts"),
    ("recaptcha", "Google reCAPTCHA", "captcha"),
    ("googleadservices.com", "Google Ads", "ads"),
    ("googlesyndication.com", "Google AdSense", "ads"),
    ("doubleclick.net", "Google Ad Manager", "ads"),
    ("cloudflare.com", "Cloudflare", "cdn"),
    ("cloudflareinsights.com", "Cloudflare Web Analytics", "analytics"),
    ("jsdelivr.net", "jsDelivr", "cdn"),
    ("unpkg.com", "unpkg", "cdn"),
    ("cdnjs.cloudflare.com", "cdnjs", "cdn"),
    ("facebook.net", "Facebook SDK", "social"),
    ("platform.twitter.com", "Twitter/X", "social"),
    ("hotjar.com", "Hotjar", "analytics"),
    ("newrelic.com", "New Relic", "monitoring"),
    ("sentry.io", "Sentry", "monitoring"),
    ("segment.io", "Segment", "analytics"),
    ("mixpanel.com", "Mixpanel", "analytics"),
    ("amplitude.com", "Amplitude", "analytics"),
    ("fullstory.com", "FullStory", "analytics"),
    ("optimizely.com", "Optimizely", "testing"),
    ("matomo", "Matomo", "analytics"),
    ("plausible.io", "Plausible", "analytics"),
    ("umami.is", "Umami", "analytics"),
    ("intercom.io", "Intercom", "support"),
    ("crisp.chat", "Crisp", "support"),
    ("zendesk.com", "Zendesk", "support"),
    ("wordpress.org", "WordPress", "cms"),
    ("wp.com", "WordPress.com", "cms"),
    ("shopify.com", "Shopify", "ecommerce"),
    ("squarespace.com", "Squarespace", "ecommerce"),
    ("wix.com", "Wix", "ecommerce"),
    ("amazonaws.com", "AWS", "cloud"),
    ("azureedge.net", "Microsoft Azure", "cloud"),
    ("akamai", "Akamai", "cdn"),
    ("fastly.net", "Fastly", "cdn"),
    ("stackpathcdn.com", "StackPath", "cdn"),
    ("yandex.ru", "Yandex", "search"),
    ("baidu.com", "Baidu", "search"),
    ("bing.com", "Bing", "search"),
    ("pubmatic.com", "PubMatic", "ads"),
    ("criteo.com", "Criteo", "ads"),
    ("taboola.com", "Taboola", "ads"),
    ("outbrain.com", "Outbrain", "ads"),
)


@dataclass
class ResourceData:
    resource_type: str
    url: str
    host: str | None
    integrity: str | None
    crossorigin: str | None
    async_attr: bool
    defer_attr: bool
    provider: str | None
    category: str | None


def fingerprint(url: str) -> tuple[str | None, str | None]:
    """Identify the provider and category of an external resource URL."""
    lower = url.lower()
    for fragment, provider, category in PROVIDER_RULES:
        if fragment in lower:
            return provider, category
    return None, None


def _absolute(base_url: str, ref: str) -> str:
    if ref.startswith("http"):
        return ref
    if ref.startswith("//"):
        return f"https:{ref}"
    return str(httpx.URL(base_url).join(ref))


def _host_of(url: str) -> str | None:
    try:
        return httpx.URL(url).host
    except Exception:
        return None


def inventory_resources(html: str, page_url: str) -> List[ResourceData]:
    """Extract external resources (scripts, iframes, stylesheets, preconnects)."""
    soup = BeautifulSoup(html, "lxml")
    resources: List[ResourceData] = []
    seen: set[str] = set()

    def add(resource_type: str, url: str, **attrs) -> None:
        if not url or url.startswith(("data:", "blob:", "about:")):
            return
        absolute = _absolute(page_url, url)
        key = f"{resource_type}:{absolute}"
        if key in seen:
            return
        seen.add(key)
        provider, category = fingerprint(absolute)
        resources.append(
            ResourceData(
                resource_type=resource_type,
                url=absolute,
                host=_host_of(absolute),
                integrity=attrs.get("integrity"),
                crossorigin=attrs.get("crossorigin"),
                async_attr=bool(attrs.get("async_attr")),
                defer_attr=bool(attrs.get("defer_attr")),
                provider=provider,
                category=category,
            )
        )

    for tag in soup.find_all("script", src=True):
        add(
            "script",
            tag.get("src"),
            integrity=tag.get("integrity"),
            crossorigin=tag.get("crossorigin"),
            async_attr=tag.get("async") is not None,
            defer_attr=tag.get("defer") is not None,
        )

    for tag in soup.find_all("iframe", src=True):
        add("iframe", tag.get("src"))

    for tag in soup.find_all("link", rel=True):
        rel = " ".join(tag.get("rel", []))
        if "stylesheet" in rel:
            add(
                "stylesheet",
                tag.get("href"),
                integrity=tag.get("integrity"),
                crossorigin=tag.get("crossorigin"),
            )
        elif "preconnect" in rel:
            add("preconnect", tag.get("href"))

    return resources


async def fetch_html(target: str, timeout: float = 20.0) -> tuple[str, str]:
    url = target if "://" in target else f"https://{target}"
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(timeout),
            headers={"User-Agent": DEFAULT_USER_AGENT},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return str(response.url), response.text
    except httpx.HTTPError as exc:
        raise TargetError(f"Failed to fetch target: {exc}") from exc


async def analyze_target(target: str) -> dict:
    final_url, html = await fetch_html(target)
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    resources = inventory_resources(html, final_url)

    return {
        "final_url": final_url,
        "title": title,
        "resources": resources,
    }
