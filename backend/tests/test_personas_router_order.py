"""Route-order regressions: static /api/personas paths vs ``/{archetype_id}``."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


def test_designer_list_not_shadowed_by_archetype_route() -> None:
    """GET /designer must list designer personas, not treat ``designer`` as archetype id."""
    with patch(
        "app.personas.router.persona_designer.list_custom_personas",
        new_callable=AsyncMock,
        return_value=[],
    ) as list_custom_mock:
        with TestClient(app) as client:
            r = client.get("/api/personas/designer")
        assert r.status_code == 200
        assert r.json() == []
        list_custom_mock.assert_awaited_once()
