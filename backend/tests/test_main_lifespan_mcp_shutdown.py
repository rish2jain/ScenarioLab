"""Lifespan shutdown must cancel MCP background simulation tasks."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


def test_lifespan_shutdown_calls_mcp_background_simulation_cleanup():
    with patch(
        "app.main.mcp_server.shutdown_background_simulation",
        new_callable=AsyncMock,
    ) as shutdown_mock:
        with TestClient(app):
            pass
        shutdown_mock.assert_awaited_once()
