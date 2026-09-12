"""Shared pytest fixtures: isolated SQLite database + TestClient.

The environment is configured before any ``app.*`` import so the engine binds to
a temporary SQLite file instead of the development database.
"""

import os
import tempfile
from pathlib import Path

_TMP_DIR = tempfile.mkdtemp(prefix="musha-tests-")
os.environ["DB_DRIVER"] = "sqlite"
os.environ["DB_PATH"] = str(Path(_TMP_DIR) / "test.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    """Recreate the schema and clear middleware state before every test."""
    from app import database, models, security

    models.Base.metadata.drop_all(bind=database.engine)
    models.Base.metadata.create_all(bind=database.engine)
    security.reset_rate_limiter()
    yield


@pytest.fixture()
def client():
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def fake_analyzer(monkeypatch):
    """Replace the network analyzer with canned resources."""
    from app import analyzer

    async def fake_analyze(target: str) -> dict:
        return {
            "final_url": "https://example.com/",
            "title": "Example Domain",
            "resources": [
                analyzer.ResourceData(
                    resource_type="script",
                    url="https://cdn.example.com/app.js",
                    host="cdn.example.com",
                    integrity="sha384-abc",
                    crossorigin="anonymous",
                    async_attr=True,
                    defer_attr=False,
                    provider=None,
                    category=None,
                ),
                analyzer.ResourceData(
                    resource_type="stylesheet",
                    url="https://example.com/app.css",
                    host="example.com",
                    integrity=None,
                    crossorigin=None,
                    async_attr=False,
                    defer_attr=False,
                    provider=None,
                    category=None,
                ),
            ],
        }

    monkeypatch.setattr(analyzer, "analyze_target", fake_analyze)
    return fake_analyze


@pytest.fixture()
def create_analysis(client):
    """POST a valid inventory run and return the parsed response."""

    def _create(target: str = "https://example.com") -> dict:
        response = client.post("/api/content/inventory", json={"target": target})
        assert response.status_code == 200, response.text
        return response.json()

    return _create
