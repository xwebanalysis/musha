"""API integration tests for structural diff and content drift endpoints."""

from datetime import datetime, timedelta

from app import database, models


def _resource(
    resource_type: str,
    url: str,
    provider: str | None = None,
    category: str | None = None,
    integrity: str | None = None,
    crossorigin: str | None = None,
    async_attr: bool = False,
    defer_attr: bool = False,
) -> models.ThirdPartyResource:
    return models.ThirdPartyResource(
        resource_type=resource_type,
        url=url,
        host=url.split("//", 1)[1].split("/", 1)[0] if "//" in url else None,
        integrity=integrity,
        crossorigin=crossorigin,
        async_attr=int(async_attr),
        defer_attr=int(defer_attr),
        provider=provider,
        category=category,
    )


def _seed_analysis(
    target: str,
    resources: list[models.ThirdPartyResource],
    created_at: datetime | None = None,
    status: str = "COMPLETED",
) -> int:
    db = database.SessionLocal()
    try:
        analysis = models.ContentAnalysis(
            target=target,
            status=status,
            created_at=created_at or datetime(2026, 9, 20, 10, 0, 0),
        )
        db.add(analysis)
        db.flush()
        for resource in resources:
            resource.analysis_id = analysis.id
            db.add(resource)
        db.commit()
        return analysis.id
    finally:
        db.close()


def test_diff_endpoint_classifies_changes(client, fake_analyzer, create_analysis, monkeypatch):
    # Two REST analyses with different targets -> fake_analyzer must vary per
    # target, so patch it again here.
    from app import analyzer

    def variants(target: str) -> list:
        if "one" in target:
            return [
                analyzer.ResourceData(
                    resource_type="script",
                    url="https://cdn.example.com/shared.js",
                    host="cdn.example.com",
                    integrity=None,
                    crossorigin=None,
                    async_attr=True,
                    defer_attr=False,
                    provider="cdnjs",
                    category="cdn",
                ),
                analyzer.ResourceData(
                    resource_type="stylesheet",
                    url="https://one.example/only-one.css",
                    host="one.example",
                    integrity=None,
                    crossorigin=None,
                    async_attr=False,
                    defer_attr=False,
                    provider=None,
                    category=None,
                ),
            ]
        return [
            analyzer.ResourceData(
                resource_type="script",
                url="https://cdn.example.com/shared.js",
                host="cdn.example.com",
                integrity="sha384-abc",
                crossorigin="anonymous",
                async_attr=False,
                defer_attr=True,
                provider="Cloudflare",
                category="cdn",
            ),
            analyzer.ResourceData(
                resource_type="iframe",
                url="https://two.example/embed",
                host="two.example",
                integrity=None,
                crossorigin=None,
                async_attr=False,
                defer_attr=False,
                provider=None,
                category=None,
            ),
        ]

    async def fake_analyze(target: str) -> dict:
        return {
            "final_url": target,
            "title": "Diff Target",
            "resources": variants(target),
        }

    monkeypatch.setattr(analyzer, "analyze_target", fake_analyze)

    base = client.post("/api/content/inventory", json={"target": "https://one.example"}).json()
    other = client.post("/api/content/inventory", json={"target": "https://two.example"}).json()

    base_id = base["analysis"]["id"]
    other_id = other["analysis"]["id"]

    response = client.get(f"/api/analyses/{base_id}/diff", params={"against": other_id})
    assert response.status_code == 200
    body = response.json()

    assert body["base"]["id"] == base_id
    assert body["against"]["id"] == other_id

    assert body["summary"]["base_total"] == 2
    assert body["summary"]["other_total"] == 2
    assert body["summary"]["added_count"] == 1
    assert body["summary"]["removed_count"] == 1
    assert body["summary"]["modified_count"] == 1
    assert body["summary"]["unchanged_count"] == 0
    assert body["summary"]["provider_changes_count"] == 1
    assert body["summary"]["similarity_score"] == 0.0

    assert [item["url"] for item in body["added"]] == ["https://two.example/embed"]
    assert [item["url"] for item in body["removed"]] == ["https://one.example/only-one.css"]

    modified = body["modified"][0]
    assert modified["url"] == "https://cdn.example.com/shared.js"
    assert set(modified["changes"]) == {"async_attr", "defer_attr", "integrity", "crossorigin"}
    assert modified["provider_changed"] is True
    assert modified["provider_base"] == "cdnjs"
    assert modified["provider_other"] == "Cloudflare"
    assert body["provider_changes"][0]["url"] == "https://cdn.example.com/shared.js"


def test_diff_requires_against_and_valid_ids(client, fake_analyzer, create_analysis):
    created = create_analysis()
    analysis_id = created["analysis"]["id"]

    missing = client.get(f"/api/analyses/{analysis_id}/diff")
    assert missing.status_code == 422

    unknown = client.get(f"/api/analyses/{analysis_id}/diff", params={"against": 9999})
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "NOT_FOUND"

    self_diff = client.get(f"/api/analyses/{analysis_id}/diff", params={"against": analysis_id})
    assert self_diff.status_code == 400
    assert self_diff.json()["error"]["code"] == "BAD_REQUEST"


def test_diff_ignores_cache_buster_noise(client):
    first = _seed_analysis(
        "https://noise.example",
        [_resource("script", "https://cdn.example.com/app.js?_=111&utm_source=x")],
    )
    second = _seed_analysis(
        "https://noise.example",
        [_resource("script", "https://cdn.example.com/app.js?_=222&utm_source=y")],
    )
    response = client.get(f"/api/analyses/{first}/diff", params={"against": second})
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["unchanged_count"] == 1
    assert body["summary"]["similarity_score"] == 100.0
    assert body["added"] == [] and body["removed"] == [] and body["modified"] == []


def test_drift_endpoint_over_consecutive_analyses(client):
    day = datetime(2026, 9, 20, 10, 0, 0)
    first = _seed_analysis(
        "https://example.com",
        [
            _resource("script", "https://www.googletagmanager.com/gtag/js", provider="Google Tag Manager", category="tag-manager"),
            _resource("stylesheet", "https://example.com/app.css"),
        ],
        created_at=day,
    )
    _seed_analysis(
        "https://example.com",
        [
            _resource("script", "https://www.googletagmanager.com/gtag/js", provider="Google Tag Manager", category="tag-manager"),
            _resource("script", "https://cdn.jsdelivr.net/npm/lodash/lodash.min.js", provider="jsDelivr", category="cdn"),
        ],
        created_at=day + timedelta(days=1),
    )
    third = _seed_analysis(
        "https://example.com",
        [_resource("script", "https://cdn.jsdelivr.net/npm/lodash/lodash.min.js", provider="jsDelivr", category="cdn")],
        created_at=day + timedelta(days=2),
    )

    response = client.get("/api/targets/example.com/drift")
    assert response.status_code == 200
    body = response.json()

    assert body["domain"] == "example.com"
    assert body["summary"]["analysis_count"] == 3
    assert body["summary"]["severity"] == "high"
    assert body["summary"]["providers_removed"] == ["Google Tag Manager"]
    assert "Google Tag Manager" in body["summary"]["alert"]

    steps = body["steps"]
    assert [step["from_analysis_id"] for step in steps] == [first, first + 1]
    assert [step["to_analysis_id"] for step in steps] == [first + 1, third]
    assert steps[0]["severity"] == "low"  # 2 -> 2 resources, provider added only
    assert steps[1]["severity"] == "high"  # provider removed + count drop
    assert steps[1]["resource_delta"] == -1
    assert steps[1]["resource_delta_pct"] == -50.0
    assert "providers removed: Google Tag Manager" in steps[1]["alert"]


def test_drift_accepts_www_and_url_domains(client):
    _seed_analysis(
        "https://www.example.com",
        [_resource("script", "https://www.example.com/app.js")],
        created_at=datetime(2026, 9, 20, 10, 0, 0),
    )
    _seed_analysis(
        "https://www.example.com",
        [_resource("script", "https://www.example.com/app.js")],
        created_at=datetime(2026, 9, 21, 10, 0, 0),
    )
    response = client.get("/api/targets/example.com/drift")
    assert response.status_code == 200
    assert response.json()["summary"]["analysis_count"] == 2
    assert response.json()["summary"]["severity"] == "low"


def test_drift_unknown_domain_404(client):
    response = client.get("/api/targets/unknown.example/drift")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_drift_skips_failed_analyses(client):
    _seed_analysis(
        "https://failed.example",
        [_resource("script", "https://failed.example/app.js")],
        created_at=datetime(2026, 9, 20, 10, 0, 0),
    )
    _seed_analysis(
        "https://failed.example",
        [],
        created_at=datetime(2026, 9, 21, 10, 0, 0),
        status="ERROR",
    )
    response = client.get("/api/targets/failed.example/drift")
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["analysis_count"] == 1
    assert "at least two analyses" in body["summary"]["alert"]
