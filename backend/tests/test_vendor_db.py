"""Tests for the vendor classification database (app/data/vendors.json)."""

from app import vendor_db
from app.analyzer import fingerprint
from app.vendor_db import DATA_PATH, load


def test_database_loads_from_json():
    db = load(DATA_PATH)
    assert len(db) >= 45
    total_fragments = sum(len(v["fragments"]) for v in db)
    assert total_fragments >= 45
    for vendor in db:
        assert vendor["provider"]
        assert vendor["category"]
        assert vendor["fragments"]


def test_all_legacy_rules_migrated():
    """Every legacy PROVIDER_RULES entry must classify to the same vendor.

    Fragment URLs with a dot are rendered as hosts; the others as paths, so
    each legacy fragment gets a realistic URL to match against.
    """
    legacy_rules = [
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
    ]
    assert len(legacy_rules) >= 45

    for fragment, provider, category in legacy_rules:
        if "." in fragment and "/" not in fragment:
            url = f"https://{fragment}/asset.js"
        else:
            url = f"https://example.com/{fragment}"
        assert fingerprint(url) == (provider, category), f"rule lost: {fragment} -> {url}"


def test_classify_returns_score_and_rule():
    match = vendor_db.classify("https://cdn.jsdelivr.net/npm/lodash@4/lodash.min.js")
    assert match is not None
    assert match[0] == "jsDelivr"
    assert match[1] == "cdn"
    # cdn.jsdelivr.net is a subdomain of jsdelivr.net -> host-suffix score
    assert match[2] == vendor_db.SCORE_HOST_SUFFIX
    exact = vendor_db.classify("https://jsdelivr.net/npm/lodash@4/lodash.min.js")
    assert exact[2] == vendor_db.SCORE_HOST_EXACT


def test_host_exact_match_beats_host_suffix_match():
    # cdnjs.cloudflare.com contains "cloudflare.com", but the exact host rule
    # for cdnjs must win over the subdomain-suffix rule for Cloudflare.
    assert fingerprint("https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js") == (
        "cdnjs",
        "cdn",
    )
    # a bare Cloudflare asset still resolves to Cloudflare
    assert fingerprint("https://challenges.cloudflare.com/turnstile/v0/api.js") == (
        "Cloudflare",
        "cdn",
    )


def test_path_level_match_scores_lower_but_works():
    # "googleapis.com/css" lives in the path of fonts.googleapis.com URLs; the
    # host-level rule "fonts.googleapis.com" must win the scoring anyway.
    assert fingerprint("https://fonts.googleapis.com/css2?family=Roboto") == (
        "Google Fonts",
        "fonts",
    )
    # a path-only hit still classifies (legacy substring behavior)
    assert fingerprint("https://example.com/assets/segment.io/bundle.js") == (
        "Segment",
        "analytics",
    )


def test_unknown_urls_are_not_classified():
    assert fingerprint("https://example.com/custom.js") == (None, None)
    assert vendor_db.classify("https://example.org/plain/app.css") is None


def test_classification_is_case_insensitive():
    assert fingerprint("https://WWW.GOOGLETAGMANAGER.COM/gtag/js?id=x") == (
        "Google Tag Manager",
        "tag-manager",
    )
