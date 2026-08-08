"""Unit tests for musha analyzer (no network)."""

from app.analyzer import fingerprint, inventory_resources

SAMPLE_HTML = """
<html>
<head>
  <title>Test</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="stylesheet" href="/app.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5/dist/bootstrap.min.css">
</head>
<body>
  <script src="https://www.googletagmanager.com/gtag/js?id=G-XXXX" async></script>
  <script src="/js/app.js" defer></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js"></script>
  <iframe src="https://www.youtube.com/embed/abc123"></iframe>
  <script src="data:text/javascript,alert(1)"></script>
</body>
</html>
"""


def test_fingerprint_providers():
    assert fingerprint("https://www.googletagmanager.com/gtag/js") == ("Google Tag Manager", "tag-manager")
    assert fingerprint("https://cdn.jsdelivr.net/npm/x") == ("jsDelivr", "cdn")
    assert fingerprint("https://example.com/custom.js") == (None, None)


def test_inventory_extracts_and_deduplicates():
    resources = inventory_resources(SAMPLE_HTML, "https://example.com/")
    by_type: dict[str, list] = {}
    for r in resources:
        by_type.setdefault(r.resource_type, []).append(r)

    assert len(by_type["script"]) == 3
    assert len(by_type["stylesheet"]) == 2
    assert len(by_type["iframe"]) == 1
    assert len(by_type["preconnect"]) == 1

    gtag = by_type["script"][0]
    assert gtag.provider == "Google Tag Manager"
    assert gtag.async_attr is True
    assert gtag.host == "www.googletagmanager.com"

    local = by_type["script"][1]
    assert local.url == "https://example.com/js/app.js"
    assert local.provider is None
    assert local.defer_attr is True


def test_relative_urls_resolved():
    resources = inventory_resources(SAMPLE_HTML, "https://example.com/")
    stylesheets = [r for r in resources if r.resource_type == "stylesheet"]
    assert any(r.url == "https://example.com/app.css" for r in stylesheets)


def test_protocol_relative_urls():
    html = '<script src="//cdn.example.com/x.js"></script>'
    resources = inventory_resources(html, "https://example.com/")
    assert resources[0].url == "https://cdn.example.com/x.js"


def test_integrity_and_crossorigin_captured():
    html = (
        '<script src="https://cdn.example.com/x.js" integrity="sha384-abc" '
        'crossorigin="anonymous"></script>'
    )
    resources = inventory_resources(html, "https://example.com/")
    assert resources[0].integrity == "sha384-abc"
    assert resources[0].crossorigin == "anonymous"
