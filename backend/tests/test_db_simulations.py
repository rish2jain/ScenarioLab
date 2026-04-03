"""Tests for domain-specific repositories in app/db/.

Tests SimulationRepository via the new app.db.simulations module,
with a temporary DB using init_schema().

Also exercises SeedRepository, AnnotationRepository, ChatHistoryRepository,
and AgentMemoryRepository at a basic create/read/delete level.
"""

from unittest.mock import patch

import pytest

import app.db.connection as conn_mod
from app.db.simulations import SimulationRepository
from app.simulation.models import (
    AgentConfig,
    EnvironmentType,
    SimulationConfig,
    SimulationState,
    SimulationStatus,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sim_config():
    return SimulationConfig(
        name="Test Sim",
        description="A domain-repo test",
        environment_type=EnvironmentType.BOARDROOM,
        agents=[AgentConfig(name="CEO", archetype_id="ceo")],
        total_rounds=5,
    )


@pytest.fixture
def sim_state(sim_config):
    return SimulationState(config=sim_config, status=SimulationStatus.READY)


@pytest.fixture
async def sim_repo(tmp_path):
    """Initialize a temp DB and return a SimulationRepository."""
    db_path = tmp_path / "test.db"
    with patch.object(conn_mod, "DB_PATH", db_path), patch.object(
        conn_mod, "_DB_DIR", tmp_path
    ):
        conn_mod._db = None
        await conn_mod.init_schema()
        yield SimulationRepository()
        await conn_mod.close_database()
    conn_mod._db = None


# ---------------------------------------------------------------------------
# SimulationRepository
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestSimulationRepository:
    async def test_save_and_get(self, sim_repo, sim_state):
        await sim_repo.save(sim_state)
        loaded = await sim_repo.get(sim_state.config.id)
        assert loaded is not None
        assert loaded.config.id == sim_state.config.id
        assert loaded.config.name == "Test Sim"
        assert loaded.status == SimulationStatus.READY

    async def test_get_nonexistent(self, sim_repo):
        result = await sim_repo.get("nonexistent-id")
        assert result is None

    async def test_list_all_empty(self, sim_repo):
        summaries = await sim_repo.list_all()
        assert summaries == []

    async def test_list_all(self, sim_repo, sim_config):
        for i in range(3):
            config = sim_config.model_copy(
                update={"id": f"sim-{i}", "name": f"Sim {i}"}
            )
            state = SimulationState(config=config, status=SimulationStatus.READY)
            await sim_repo.save(state)

        summaries = await sim_repo.list_all()
        assert len(summaries) == 3
        names = {s["name"] for s in summaries}
        assert names == {"Sim 0", "Sim 1", "Sim 2"}

    async def test_delete(self, sim_repo, sim_state):
        await sim_repo.save(sim_state)
        deleted = await sim_repo.delete(sim_state.config.id)
        assert deleted is True
        assert await sim_repo.get(sim_state.config.id) is None

    async def test_delete_nonexistent(self, sim_repo):
        assert await sim_repo.delete("nonexistent") is False

    async def test_update_status(self, sim_repo, sim_state):
        await sim_repo.save(sim_state)
        await sim_repo.update_status(sim_state.config.id, "running")
        loaded = await sim_repo.get(sim_state.config.id)
        assert loaded is not None
        assert loaded.status == SimulationStatus.RUNNING

    async def test_upsert_overwrites(self, sim_repo, sim_state):
        await sim_repo.save(sim_state)
        sim_state.status = SimulationStatus.COMPLETED
        sim_state.current_round = 5
        await sim_repo.save(sim_state)
        loaded = await sim_repo.get(sim_state.config.id)
        assert loaded is not None
        assert loaded.status == SimulationStatus.COMPLETED
        assert loaded.current_round == 5

    async def test_list_all_includes_metadata(self, sim_repo, sim_state):
        await sim_repo.save(sim_state)
        summaries = await sim_repo.list_all()
        assert len(summaries) == 1
        s = summaries[0]
        # Required keys
        for key in ("id", "name", "status", "environment_type", "created_at", "updated_at"):
            assert key in s, f"Missing key '{key}' in summary"


# ---------------------------------------------------------------------------
# AuditTrailRepository (basic smoke test)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_save_and_retrieve(tmp_path):
    db_path = tmp_path / "audit_test.db"
    with patch.object(conn_mod, "DB_PATH", db_path), patch.object(
        conn_mod, "_DB_DIR", tmp_path
    ):
        conn_mod._db = None
        await conn_mod.init_schema()
        try:
            from app.db.audit import AuditTrailRepository

            repo = AuditTrailRepository()
            event = {
                "event_id": "ev-1",
                "simulation_id": "sim-1",
                "event_type": "turn_complete",
                "timestamp": "2026-01-01T00:00:00+00:00",
                "actor": "engine",
                "details": {"round": 1},
                "previous_hash": "0" * 64,
                "hash": "a" * 64,
            }
            await repo.save_event(event)
            events = await repo.get_events("sim-1")
            assert len(events) == 1
            assert events[0]["event_id"] == "ev-1"

            # Single event — chain is trivially valid
            ok, msg = await repo.verify_integrity("sim-1")
            assert ok, msg
        finally:
            await conn_mod.close_database()
    conn_mod._db = None


# ---------------------------------------------------------------------------
# ChatHistoryRepository (basic smoke test)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_save_and_retrieve(tmp_path):
    db_path = tmp_path / "chat_test.db"
    with patch.object(conn_mod, "DB_PATH", db_path), patch.object(
        conn_mod, "_DB_DIR", tmp_path
    ):
        conn_mod._db = None
        await conn_mod.init_schema()
        try:
            from app.db.chat import ChatHistoryRepository

            repo = ChatHistoryRepository()
            msg_id = await repo.save_message(
                simulation_id="sim-1",
                agent_id="agent-a",
                agent_name="CEO",
                user_message="What is your strategy?",
                agent_response="We will expand globally.",
                timestamp="2026-01-01T00:00:00+00:00",
            )
            assert msg_id is not None
            history = await repo.get_history("sim-1")
            assert len(history) == 1
            assert history[0]["user_message"] == "What is your strategy?"

            count = await repo.clear_history("sim-1")
            assert count == 1
            assert await repo.get_history("sim-1") == []
        finally:
            await conn_mod.close_database()
    conn_mod._db = None


# ---------------------------------------------------------------------------
# AgentMemoryRepository (basic smoke test)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_memory_save_and_search(tmp_path):
    db_path = tmp_path / "mem_test.db"
    with patch.object(conn_mod, "DB_PATH", db_path), patch.object(
        conn_mod, "_DB_DIR", tmp_path
    ):
        conn_mod._db = None
        await conn_mod.init_schema()
        try:
            from app.db.memories import AgentMemoryRepository

            repo = AgentMemoryRepository()
            mem_id = await repo.save_memory(
                simulation_id="sim-1",
                agent_id="agent-a",
                round_number=1,
                content="The market is highly competitive.",
                memory_type="observation",
                timestamp="2026-01-01T00:00:00+00:00",
            )
            assert mem_id is not None

            memories = await repo.get_memories("sim-1", "agent-a")
            assert len(memories) == 1

            results = await repo.search_memories("sim-1", "agent-a", "competitive")
            assert len(results) == 1

            empty = await repo.search_memories("sim-1", "agent-a", "unicorn")
            assert empty == []
        finally:
            await conn_mod.close_database()
    conn_mod._db = None
