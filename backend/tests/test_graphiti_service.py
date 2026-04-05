"""Tests for Graphiti integration helpers (no live Neo4j/Graphiti required)."""

import asyncio
import sys
import types
from unittest.mock import MagicMock

import pytest

from app.graph import graphiti_service as graphiti_service_mod
from app.graph.graphiti_service import (
    _delete_neo4j_saga_nodes_by_group_id,
    _tombstone_group_id,
    delete_simulation_graph,
    format_round_episode_body,
    ingest_round_episode,
    reset_graphiti_ingest_coordination_for_tests,
    schedule_round_episode_ingest,
    start_graphiti,
    stop_graphiti,
)
from app.simulation.models import RoundState, SimulationMessage


@pytest.fixture(autouse=True)
def _reset_graphiti_coordination() -> None:
    reset_graphiti_ingest_coordination_for_tests()
    yield
    reset_graphiti_ingest_coordination_for_tests()


@pytest.mark.asyncio
async def test_start_graphiti_noop_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.graph.graphiti_service.settings.graphiti_enabled", False)
    await start_graphiti()
    await stop_graphiti()


def test_format_round_episode_body_includes_messages() -> None:
    rs = RoundState(
        round_number=2,
        phase="vote",
        messages=[
            SimulationMessage(
                round_number=2,
                phase="presentation",
                agent_id="a1",
                agent_name="Alex",
                agent_role="CFO",
                content="We should proceed.",
            ),
        ],
        decisions=[{"outcome": "approved"}],
    )
    body = format_round_episode_body("Deal war game", "sim-uuid-1", rs)
    assert "sim-uuid-1" in body
    assert "Round: 2" in body
    assert "Alex" in body
    assert "CFO" in body
    assert "We should proceed" in body
    assert "approved" in body


@pytest.mark.asyncio
async def test_delete_neo4j_saga_nodes_by_group_id_runs_saga_detach_delete() -> None:
    """Regression: graphiti_core Node.delete_by_group_id omits Saga; helper must delete them."""
    run_calls: list[tuple[str, dict]] = []

    class FakeDriver:
        provider = "neo4j"

        async def execute_query(self, query: str, **kwargs: object) -> None:
            params = kwargs.get("params") or {}
            run_calls.append((query, dict(params)))

    await _delete_neo4j_saga_nodes_by_group_id(FakeDriver(), "sim-partition-1")

    assert any("Saga" in q for q, _ in run_calls)
    assert any(params.get("group_id") == "sim-partition-1" for _, params in run_calls)


@pytest.mark.asyncio
async def test_delete_neo4j_saga_nodes_skipped_for_non_neo4j_driver() -> None:
    class FakeDriver:
        provider = "falkordb"

        async def execute_query(self, *_a: object, **_kw: object) -> None:
            raise AssertionError("non-Neo4j driver should skip before execute_query")

    await _delete_neo4j_saga_nodes_by_group_id(FakeDriver(), "sim-x")


@pytest.mark.asyncio
async def test_ingest_skips_when_tombstoned(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.graph.graphiti_service.settings.graphiti_enabled", True)
    calls: list[object] = []

    class FakeG:
        async def add_episode(self, **kwargs: object) -> None:
            calls.append(kwargs)

    monkeypatch.setattr(graphiti_service_mod, "get_graphiti", lambda: FakeG())
    sid = "sim-tombstoned"
    _tombstone_group_id(sid)
    rs = RoundState(round_number=1, phase="discussion", messages=[], decisions=[])
    await ingest_round_episode(sid, "Name", 1, rs)
    assert calls == []


@pytest.mark.asyncio
async def test_delete_graphiti_cancels_pending_ingest(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression: cleanup must not lose to a late background ingest task."""
    monkeypatch.setattr("app.graph.graphiti_service.settings.graphiti_enabled", True)

    blocker = asyncio.Event()
    allow = asyncio.Event()
    ingest_ran_after_cancel = False

    async def slow_ingest(*_a: object, **_kw: object) -> None:
        nonlocal ingest_ran_after_cancel
        blocker.set()
        try:
            await allow.wait()
        except asyncio.CancelledError:
            raise
        ingest_ran_after_cancel = True

    monkeypatch.setattr(graphiti_service_mod, "ingest_round_episode", slow_ingest)

    class FakeDriver:
        provider = "neo4j"

        async def execute_query(self, *_a: object, **_kw: object) -> None:
            return None

    class FakeG:
        driver = FakeDriver()

    monkeypatch.setattr(graphiti_service_mod, "get_graphiti", lambda: FakeG())

    async def noop_delete(*_a: object, **_kw: object) -> None:
        return None

    saved_gc = sys.modules.get("graphiti_core")
    saved_nodes = sys.modules.get("graphiti_core.nodes")
    nodes_mod = types.ModuleType("graphiti_core.nodes")

    class _Node:
        delete_by_group_id = staticmethod(noop_delete)

    nodes_mod.Node = _Node
    gc_mod = types.ModuleType("graphiti_core")
    gc_mod.nodes = nodes_mod
    sys.modules["graphiti_core"] = gc_mod
    sys.modules["graphiti_core.nodes"] = nodes_mod

    sid = "sim-pending-ingest"
    try:
        schedule_round_episode_ingest(sid, "x", 1, MagicMock())
        await asyncio.wait_for(blocker.wait(), timeout=2.0)

        await delete_simulation_graph(sid)
        allow.set()
        await asyncio.sleep(0.05)

        assert not ingest_ran_after_cancel
    finally:
        if saved_gc is not None:
            sys.modules["graphiti_core"] = saved_gc
        else:
            sys.modules.pop("graphiti_core", None)
        if saved_nodes is not None:
            sys.modules["graphiti_core.nodes"] = saved_nodes
        else:
            sys.modules.pop("graphiti_core.nodes", None)
