"""Unit tests for structural diffing (normalization + classification)."""

from app.diffing import diff_resources, normalize_url, resource_key


def resource(
    resource_type: str,
    url: str,
    provider: str | None = None,
    category: str | None = None,
    integrity: str | None = None,
    crossorigin: str | None = None,
    async_attr: bool = False,
    defer_attr: bool = False,
    host: str | None = None,
) -> dict:
    return {
        "resource_type": resource_type,
        "url": url,
        "host": host,
        "integrity": integrity,
        "crossorigin": crossorigin,
        "async_attr": async_attr,
        "defer_attr": defer_attr,
        "provider": provider,
        "category": category,
    }


# ---------------------------------------------------------------------------
# URL normalization (volatile-node handling)
# ---------------------------------------------------------------------------


def test_normalize_drops_noise_query_tokens():
    noise = (
        "https://cdn.example.com/app.js"
        "?utm_source=newsletter&utm_medium=email&fbclid=abc&gclid=def&nonce=xyz"
        "&_=1700000000&cb=12345&ts=1700000001&token=sess&v=1.2"
    )
    assert normalize_url(noise) == "https://cdn.example.com/app.js?v=1.2"


def test_normalize_is_insensitive_to_query_order_and_case():
    a = "https://CDN.Example.com/app.js?b=2&a=1#frag"
    b = "https://cdn.example.com/app.js?a=1&b=2"
    assert normalize_url(a) == normalize_url(b) == "https://cdn.example.com/app.js?a=1&b=2"


def test_normalize_strips_default_ports_and_fragment():
    assert normalize_url("https://example.com:443/x.css#top") == "https://example.com/x.css"
    assert normalize_url("http://example.com:80/x.css") == "http://example.com/x.css"


def test_cache_buster_only_changes_do_not_churn_keys():
    assert resource_key(resource("script", "https://cdn.example.com/app.js?_=1")) == resource_key(
        resource("script", "https://cdn.example.com/app.js?_=2")
    )


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def test_added_and_removed_detection():
    base = [
        resource("script", "https://cdn.example.com/a.js"),
        resource("stylesheet", "https://example.com/site.css"),
    ]
    other = [
        resource("script", "https://cdn.example.com/a.js"),
        resource("iframe", "https://player.example.com/embed"),
    ]
    result = diff_resources(base, other)
    assert [r["url"] for r in result.added] == ["https://player.example.com/embed"]
    assert [r["url"] for r in result.removed] == ["https://example.com/site.css"]
    assert result.modified == []
    assert result.summary.added_count == 1
    assert result.summary.removed_count == 1
    assert result.summary.unchanged_count == 1
    assert result.summary.similarity_score == 50.0  # 2*1/(2+2)


def test_attribute_change_is_modified():
    base = [resource("script", "https://cdn.example.com/app.js", async_attr=False)]
    other = [
        resource(
            "script",
            "https://cdn.example.com/app.js",
            async_attr=True,
            integrity="sha384-abc",
            crossorigin="anonymous",
        )
    ]
    result = diff_resources(base, other)
    assert len(result.modified) == 1
    modified = result.modified[0]
    assert set(modified.changes) == {"async_attr", "integrity", "crossorigin"}
    assert modified.provider_changed is False
    assert result.summary.modified_count == 1
    assert result.summary.similarity_score == 0.0


def test_provider_change_is_flagged():
    base = [resource("script", "https://cdn.example.com/app.js", provider="Cloudflare", category="cdn")]
    other = [resource("script", "https://cdn.example.com/app.js", provider="cdnjs", category="cdn")]
    result = diff_resources(base, other)
    assert len(result.modified) == 1
    assert result.provider_changes[0].provider_changed is True
    assert result.summary.provider_changes_count == 1


def test_empty_inventories_are_identical():
    result = diff_resources([], [])
    assert result.summary.similarity_score == 100.0
    assert result.added == [] and result.removed == [] and result.modified == []
