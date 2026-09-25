"""Vendor classification database — structured provider rules loaded from JSON.

Rules live in ``app/data/vendors.json``: one entry per provider with its
category and a list of URL fragments. Classification scores candidate matches
so that host-level hits outrank path/URL-level hits, and the best-scoring
provider wins (ties resolve to list order). The JSON file is loaded once at
startup and cached.

The legacy ``PROVIDER_RULES`` tuple from ``analyzer.py`` (47 fragment rules)
was migrated into the JSON; ``analyzer.fingerprint`` now delegates here.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import httpx

DATA_PATH = Path(__file__).resolve().parent / "data" / "vendors.json"

# Match-location weights: the more specific the location, the higher the score.
SCORE_HOST_EXACT = 100  # fragment equals the URL host
SCORE_HOST_SUFFIX = 90  # fragment is a suffix of the host (subdomain match)
SCORE_HOST_SUBSTR = 80  # fragment appears inside the host
SCORE_PATH = 60  # fragment appears inside the path
SCORE_URL = 40  # fragment appears anywhere else in the URL

SCORE_NAMES = {
    SCORE_HOST_EXACT: "host-exact",
    SCORE_HOST_SUFFIX: "host-suffix",
    SCORE_HOST_SUBSTR: "host-substring",
    SCORE_PATH: "path",
    SCORE_URL: "url",
}


class VendorDB:
    """Loaded vendor rules with scored classification."""

    def __init__(self, vendors: List[dict]):
        self.vendors = vendors

    def __len__(self) -> int:
        return len(self.vendors)

    def __iter__(self):
        return iter(self.vendors)

    def classify(self, url: str) -> Optional[dict]:
        """Return the best-scoring match as {provider, category, score, rule}.

        Returns ``None`` when no fragment matches the URL.
        """
        lower = url.lower()
        parsed = httpx.URL(lower)
        host = parsed.host or ""
        path = parsed.path or ""

        best: Optional[dict] = None
        for index, vendor in enumerate(self.vendors):
            vendor_best: Optional[dict] = None
            for fragment in vendor.get("fragments", []):
                frag = str(fragment).lower()
                score = self._score(frag, lower, host, path)
                if score is None:
                    continue
                if vendor_best is None or score > vendor_best["score"]:
                    vendor_best = {"score": score, "fragment": frag}
            if vendor_best is None:
                continue
            if best is None or vendor_best["score"] > best["score"]:
                best = {
                    "provider": vendor["provider"],
                    "category": vendor["category"],
                    "score": vendor_best["score"],
                    "rule": vendor_best["fragment"],
                }
        return best

    @staticmethod
    def _score(fragment: str, url_lower: str, host: str, path: str) -> Optional[int]:
        if host == fragment:
            return SCORE_HOST_EXACT
        if host.endswith("." + fragment):
            return SCORE_HOST_SUFFIX
        if fragment in host:
            return SCORE_HOST_SUBSTR
        if fragment in path:
            return SCORE_PATH
        if fragment in url_lower:
            return SCORE_URL
        return None


_db: Optional[VendorDB] = None


def load(path: Path = DATA_PATH) -> VendorDB:
    """Load and validate the vendor JSON file."""
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict) or not isinstance(payload.get("vendors"), list):
        raise ValueError(f"Invalid vendor database format in {path}")
    vendors: List[dict] = []
    for entry in payload["vendors"]:
        if not entry.get("provider") or not entry.get("category") or not entry.get("fragments"):
            raise ValueError(f"Invalid vendor entry in {path}: {entry!r}")
        vendors.append(
            {
                "provider": str(entry["provider"]),
                "category": str(entry["category"]),
                "fragments": [str(f) for f in entry["fragments"]],
            }
        )
    return VendorDB(vendors)


def get_db() -> VendorDB:
    """Return the shared, lazily-loaded vendor database (singleton)."""
    global _db
    if _db is None:
        _db = load()
    return _db


def reload_db(path: Path = DATA_PATH) -> VendorDB:
    """Force a reload (used by tests to swap the data file)."""
    global _db
    _db = load(path)
    classify.cache_clear()
    return _db


@lru_cache(maxsize=4096)
def classify(url: str) -> Optional[tuple]:
    """Classify a URL into (provider, category, score) or ``None``.

    Cached: inventory runs revisit the same URLs repeatedly.
    """
    match = get_db().classify(url)
    if match is None:
        return None
    return match["provider"], match["category"], match["score"]


def fingerprint(url: str) -> tuple[Optional[str], Optional[str]]:
    """Identify the provider and category of an external resource URL."""
    match = classify(url)
    if match is None:
        return None, None
    return match[0], match[1]
