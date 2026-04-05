"""MCP Graphiti search limit parsing."""

import pytest

from app.mcp.server import ScenarioLabMCPServer


@pytest.mark.asyncio
async def test_graphiti_search_invalid_limit_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    limits: list[int] = []

    async def capture_search(simulation_id: str, query: str, limit: int) -> list:
        limits.append(limit)
        return []

    import app.config as config_module
    import app.graph.graphiti_service as graphiti_module

    monkeypatch.setattr(config_module.settings, "graphiti_enabled", True)
    monkeypatch.setattr(graphiti_module, "get_graphiti", lambda: object())
    monkeypatch.setattr(graphiti_module, "search_simulation_graph", capture_search)

    server = ScenarioLabMCPServer()
    r = await server._handle_graphiti_search(
        {
            "simulation_id": "sim-1",
            "query": "hello",
            "limit": "not-a-number",
        }
    )
    assert r.status == "success"
    assert limits == [8]


@pytest.mark.asyncio
async def test_graphiti_search_limit_clamped(monkeypatch: pytest.MonkeyPatch) -> None:
    limits: list[int] = []

    async def capture_search(simulation_id: str, query: str, limit: int) -> list:
        limits.append(limit)
        return []

    import app.config as config_module
    import app.graph.graphiti_service as graphiti_module

    monkeypatch.setattr(config_module.settings, "graphiti_enabled", True)
    monkeypatch.setattr(graphiti_module, "get_graphiti", lambda: object())
    monkeypatch.setattr(graphiti_module, "search_simulation_graph", capture_search)

    server = ScenarioLabMCPServer()
    await server._handle_graphiti_search(
        {
            "simulation_id": "sim-1",
            "query": "hello",
            "limit": 999,
        }
    )
    assert limits == [25]

    await server._handle_graphiti_search(
        {
            "simulation_id": "sim-1",
            "query": "hello",
            "limit": 0,
        }
    )
    assert limits[-1] == 1
