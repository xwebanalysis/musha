"""Structural diffing of two resource inventories.

Compares the normalized third-party resource inventories of two analyses and
classifies every resource as *added*, *removed* or *modified*. A resource is
the same resource when its type and normalized URL match; *modified* means the
URL is unchanged but tracked attributes changed (``async``/``defer``/SRI
``integrity``/``crossorigin``) or the provider classification changed.

Volatile-node handling: URL normalization strips query-string noise tokens
(campaign parameters, cache-busters, nonces, timestamps) so page loads that
only differ in those do not churn the diff.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import parse_qsl, urlsplit, urlunsplit

# Query parameters that never change the meaning of a resource reference.
NOISE_QUERY_PARAMS = {
    # campaign / ad click identifiers
    "fbclid",
    "gclid",
    "gclsrc",
    "dclid",
    "wbraid",
    "gbraid",
    "msclkid",
    "mc_cid",
    "mc_eid",
    "igshid",
    "yclid",
    "twclid",
    "ttclid",
    "sc_cid",
    "li_fat_id",
    "_hsenc",
    "_hsmi",
    "_openstat",
    # session / tracking
    "nonce",
    "token",
    "access_token",
    "session",
    "session_id",
    "sid",
    # cache busters / timestamps
    "_",
    "_t",
    "ts",
    "timestamp",
    "nocache",
    "cachebust",
    "cache_bust",
    "cb",
    "_cb",
    "bust",
    "rand",
    "rnd",
    "ver",
    "tstamp",
    "now",
}

# Prefixes treated as noise (utm_*, cmp_*, spm_*, etc.).
NOISE_QUERY_PREFIXES = ("utm_", "cmp_", "spm_", "pk_", "piwik_", "mtm_", "ga_")

TRACKED_ATTRIBUTES = ("async_attr", "defer_attr", "integrity", "crossorigin")

#: Type tag used when the resource type is empty/unknown.
UNKNOWN_TYPE = "other"


def normalize_url(url: Optional[str]) -> str:
    """Normalize a resource URL for comparison.

    - scheme and host are lowercased, default ports (80/443) removed
    - the fragment is dropped
    - volatile query-string noise tokens are removed
    - remaining query params are sorted by key (order-insensitive)
    """
    if not url:
        return ""
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    if (scheme == "http" and netloc.endswith(":80")) or (scheme == "https" and netloc.endswith(":443")):
        netloc = netloc.rsplit(":", 1)[0]
    query = _clean_query(parts.query)
    return urlunsplit((scheme, netloc, parts.path, query, ""))


def _clean_query(query: str) -> str:
    if not query:
        return ""
    kept = []
    for key, value in parse_qsl(query, keep_blank_values=True):
        lowered = key.lower()
        if lowered in NOISE_QUERY_PARAMS or lowered.startswith(NOISE_QUERY_PREFIXES):
            continue
        kept.append((key, value))
    kept.sort(key=lambda pair: pair[0])
    return "&".join(f"{key}={value}" for key, value in kept)


def resource_key(resource: dict) -> tuple[str, str]:
    """Identity key of a resource: type + normalized URL."""
    resource_type = (resource.get("resource_type") or UNKNOWN_TYPE).lower()
    return resource_type, normalize_url(resource.get("url"))


def to_resource_dict(resource) -> dict:
    """Convert an ORM row (or dict) into the canonical plain dict shape."""
    if isinstance(resource, dict):
        return resource
    return {
        "resource_type": resource.resource_type,
        "url": resource.url,
        "host": resource.host,
        "integrity": resource.integrity,
        "crossorigin": resource.crossorigin,
        "async_attr": bool(resource.async_attr),
        "defer_attr": bool(resource.defer_attr),
        "provider": resource.provider,
        "category": resource.category,
    }


@dataclass
class ModifiedResource:
    """A resource present in both inventories whose attributes changed."""

    resource_type: str
    url: str
    changes: List[str] = field(default_factory=list)
    base: dict = field(default_factory=dict)
    other: dict = field(default_factory=dict)
    provider_changed: bool = False

    @property
    def provider_base(self) -> Optional[str]:
        return self.base.get("provider")

    @property
    def provider_other(self) -> Optional[str]:
        return self.other.get("provider")


@dataclass
class DiffSummary:
    base_total: int
    other_total: int
    added_count: int
    removed_count: int
    modified_count: int
    unchanged_count: int
    provider_changes_count: int
    similarity_score: float


@dataclass
class DiffResult:
    added: List[dict]
    removed: List[dict]
    modified: List[ModifiedResource]
    summary: DiffSummary

    @property
    def provider_changes(self) -> List[ModifiedResource]:
        return [m for m in self.modified if m.provider_changed]


def diff_resources(base: List[dict], other: List[dict]) -> DiffResult:
    """Diff two resource inventories (base vs other).

    Classification:
    - *added*: present in ``other`` but not in ``base``
    - *removed*: present in ``base`` but not in ``other``
    - *modified*: same key (type + normalized URL) but tracked attributes or
      the provider classification changed
    - unchanged resources count towards the similarity score only

    The similarity score is the Dice coefficient of the two key sets scaled
    to 0-100: 2 * |intersection| / (|base| + |other|). Both inventories
    empty -> 100.
    """
    base_by_key = {}
    for resource in base:
        item = to_resource_dict(resource)
        key = resource_key(item)
        if key not in base_by_key:
            base_by_key[key] = item
    other_by_key = {}
    for resource in other:
        item = to_resource_dict(resource)
        key = resource_key(item)
        if key not in other_by_key:
            other_by_key[key] = item

    base_keys = set(base_by_key)
    other_keys = set(other_by_key)

    added = [other_by_key[key] for key in sorted(other_keys - base_keys)]
    removed = [base_by_key[key] for key in sorted(base_keys - other_keys)]

    modified: List[ModifiedResource] = []
    for key in sorted(base_keys & other_keys):
        base_item = base_by_key[key]
        other_item = other_by_key[key]
        changes = [
            attr
            for attr in TRACKED_ATTRIBUTES
            if bool(base_item.get(attr)) != bool(other_item.get(attr))
        ]
        provider_changed = (base_item.get("provider") or None) != (
            other_item.get("provider") or None
        )
        if not changes and not provider_changed:
            continue
        modified.append(
            ModifiedResource(
                resource_type=key[0],
                url=base_item.get("url") or other_item.get("url") or "",
                changes=changes,
                base=base_item,
                other=other_item,
                provider_changed=provider_changed,
            )
        )

    unchanged = len(base_keys & other_keys) - len(modified)
    total = len(base_keys) + len(other_keys)
    score = round(100 * (2 * unchanged) / total, 1) if total else 100.0

    summary = DiffSummary(
        base_total=len(base_keys),
        other_total=len(other_keys),
        added_count=len(added),
        removed_count=len(removed),
        modified_count=len(modified),
        unchanged_count=unchanged,
        provider_changes_count=len([m for m in modified if m.provider_changed]),
        similarity_score=score,
    )
    return DiffResult(added=added, removed=removed, modified=modified, summary=summary)
