"""Tests for GET /api/llm/capabilities."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.llm.capabilities_cache import CapabilitiesCache
from app.llm.router import get_capabilities_cache
from app.main import app


@pytest.fixture
def client():
    # One shared cache instance per test so repeated requests hit the same store.
    shared_cache = CapabilitiesCache(ttl_sec=60.0)
    app.dependency_overrides[get_capabilities_cache] = lambda: shared_cache
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_capabilities_endpoint_local_available(client):
    """With a configured local provider, endpoint reports hybrid_available (spec 9.2)."""
    mock_local = MagicMock()
    mock_local.test_connection = AsyncMock(return_value={"status": "ok", "message": "ok", "model": "m"})
    with patch("app.llm.router.settings") as s:
        s.local_llm_provider = "ollama"
        s.local_llm_model_name = "qwen3:14b"
        s.inference_mode = "cloud"
        with patch("app.llm.router.get_local_llm_provider", return_value=mock_local):
            r = client.get("/api/llm/capabilities")
    assert r.status_code == 200
    assert r.json()["hybrid_available"] is True


def test_capabilities_endpoint_no_local(client):
    """Without local LLM config, endpoint reports hybrid_available false (spec 9.2)."""
    with patch("app.llm.router.settings") as s:
        s.local_llm_provider = ""
        s.inference_mode = "cloud"
        r = client.get("/api/llm/capabilities")
    assert r.status_code == 200
    j = r.json()
    assert j["hybrid_available"] is False
    assert j["default_inference_mode"] == "cloud"


def test_capabilities_cache_second_call_skips_probe(client):
    mock_local = MagicMock()
    mock_local.test_connection = AsyncMock(return_value={"status": "ok", "message": "ok", "model": "m"})
    # Capabilities cache TTL uses time.monotonic() in capabilities_cache; freeze it
    # so the second request cannot expire the cache on slow or time-skewed runners.
    with patch("app.llm.capabilities_cache.time.monotonic", return_value=1000.0):
        with patch("app.llm.router.time.monotonic", return_value=1000.0):
            with patch("app.llm.router.settings") as s:
                s.local_llm_provider = "ollama"
                s.local_llm_model_name = "qwen3:14b"
                s.inference_mode = "cloud"
                with patch("app.llm.router.get_local_llm_provider", return_value=mock_local):
                    r1 = client.get("/api/llm/capabilities")
                    r2 = client.get("/api/llm/capabilities")
    assert r1.status_code == 200, "first /api/llm/capabilities response"
    assert r2.status_code == 200, "second /api/llm/capabilities response"
    assert r1.json()["hybrid_available"] is True
    assert mock_local.test_connection.await_count == 1
