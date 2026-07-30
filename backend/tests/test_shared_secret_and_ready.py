"""Shared-secret auth middleware and readiness endpoint."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import app


@pytest.fixture
def secret_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    s = Settings(_env_file=None)
    s.api_shared_secret = "test-secret-value"
    monkeypatch.setattr("app.middleware_auth.settings", s)
    monkeypatch.setattr("app.main.settings", s)
    return s


def test_health_open_even_with_secret(secret_settings: Settings):
    with TestClient(app) as client:
        r = client.get("/api/health")
        assert r.status_code == 200


def test_shared_secret_blocks_api_without_header(secret_settings: Settings):
    with TestClient(app) as client:
        r = client.get("/api/playbooks")
        assert r.status_code == 401


def test_shared_secret_allows_with_header(secret_settings: Settings):
    with TestClient(app) as client:
        r = client.get(
            "/api/playbooks",
            headers={"X-ScenarioLab-Secret": "test-secret-value"},
        )
        assert r.status_code != 401


def test_shared_secret_allows_bearer(secret_settings: Settings):
    with TestClient(app) as client:
        r = client.get(
            "/api/playbooks",
            headers={"Authorization": "Bearer test-secret-value"},
        )
        assert r.status_code != 401


def test_ready_endpoint_reports_sqlite():
    with TestClient(app) as client:
        r = client.get("/api/ready")
        assert r.status_code in (200, 503)
        body = r.json()
        assert "checks" in body
        assert "sqlite" in body["checks"]
        assert "neo4j" in body["checks"]
        assert body["checks"]["neo4j"] in ("ok", "skipped", "error")


def test_ready_neo4j_uses_public_verify_when_connected(monkeypatch: pytest.MonkeyPatch):
    neo = MagicMock()
    neo.is_connected = True
    neo.verify_connectivity = AsyncMock()
    neo.close = AsyncMock()

    with TestClient(app) as client:
        # Lifespan may clear neo4j_client; set after startup.
        monkeypatch.setattr("app.main.neo4j_client", neo)
        r = client.get("/api/ready")

    assert r.status_code in (200, 503)
    assert r.json()["checks"]["neo4j"] == "ok"
    neo.verify_connectivity.assert_awaited_once()


def test_ready_neo4j_skipped_when_client_not_connected(monkeypatch: pytest.MonkeyPatch):
    neo = MagicMock()
    neo.is_connected = False
    neo.verify_connectivity = AsyncMock()
    neo.close = AsyncMock()

    with TestClient(app) as client:
        monkeypatch.setattr("app.main.neo4j_client", neo)
        r = client.get("/api/ready")

    body = r.json()
    assert body["checks"]["neo4j"] == "skipped"
    neo.verify_connectivity.assert_not_awaited()


@pytest.mark.asyncio
async def test_docs_disabled_when_not_debug(monkeypatch: pytest.MonkeyPatch):
    # App was constructed at import with settings.debug; docs_url is fixed.
    # When debug is False (default), openapi should be None on the app object.
    from app.main import app as application

    if not Settings(_env_file=None).debug:
        assert application.docs_url is None
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/docs")
            assert r.status_code == 404


def test_ready_sqlite_error_hides_exception_details(monkeypatch: pytest.MonkeyPatch):
    async def boom():
        raise RuntimeError("sqlite disk full path=/secret/db")

    monkeypatch.setattr("app.main.get_db", boom)
    monkeypatch.setattr("app.main.settings.debug", True)

    with TestClient(app) as client:
        r = client.get("/api/ready")

    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "degraded"
    assert body["checks"]["sqlite"] == "error"
    assert "disk full" not in body["checks"]["sqlite"]
    assert "/secret" not in str(body)


def test_shared_secret_protects_docs_routes(secret_settings: Settings):
    with TestClient(app) as client:
        for path in ("/docs", "/redoc", "/openapi.json"):
            r = client.get(path)
            assert r.status_code == 401, path


def test_shared_secret_401_includes_security_headers(secret_settings: Settings):
    with TestClient(app) as client:
        r = client.get("/api/playbooks")
    assert r.status_code == 401
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
