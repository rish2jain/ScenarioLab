"""Tests for domain-specific repositories in app/db/.

Tests SimulationRepository via the new app.db.simulations module,
with a temporary DB using init_schema().

Also exercises AuditTrailRepository, ChatHistoryRepository, and
AgentMemoryRepository at a basic create/read/delete level.
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
    with patch.object(conn_mod, "DB_PATH", db_path), patch.object(conn_mod, "_DB_DIR", tmp_path):
        await conn_mod.close_database()  # safe no-op if not yet open
        await conn_mod.init_schema()
        yield SimulationRepository()
        await conn_mod.close_database()


@pytest.fixture
async def temp_db(tmp_path):
    """Initialize a fresh temp DB, yield, then tear down.

    Shared by the AuditTrail, Chat, and Memory smoke tests to avoid
    duplicating setup/teardown boilerplate in each test function.
    """
    db_path = tmp_path / "temp.db"
    with patch.object(conn_mod, "DB_PATH", db_path), patch.object(conn_mod, "_DB_DIR", tmp_path):
        await conn_mod.close_database()  # safe no-op if not yet open
        await conn_mod.init_schema()
        yield
        await conn_mod.close_database()


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
            config = sim_config.model_copy(update={"id": f"sim-{i}", "name": f"Sim {i}"})
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

    async def test_list_all_current_round_from_state_not_config_cap(self, sim_repo, sim_state):
        """Persisted summaries must show real progress, not total_rounds for both fields."""
        await sim_repo.save(sim_state)
        summaries = await sim_repo.list_all()
        assert summaries[0]["current_round"] == 0
        assert summaries[0]["total_rounds"] == 5

        sim_state.current_round = 2
        await sim_repo.save(sim_state)
        summaries = await sim_repo.list_all()
        assert summaries[0]["current_round"] == 2
        assert summaries[0]["total_rounds"] == 5


# ---------------------------------------------------------------------------
# AuditTrailRepository (basic smoke test)
# ---------------------------------------------------------------------------


def test_audit_event_hash_matches_canonical_function():
    """DB verification must use the same digest as runtime AuditEvent."""
    from app.db.audit import AuditTrailRepository, compute_audit_event_hash
    from app.simulation.audit_trail import (
        GENESIS_HASH,
        AuditEvent,
        AuditEventType,
    )

    event = AuditEvent(
        simulation_id="s1",
        event_type=AuditEventType.SIMULATION_START,
        actor="user",
        details={"foo": 1},
        previous_hash=GENESIS_HASH,
    )
    assert event.hash == compute_audit_event_hash(
        previous_hash=GENESIS_HASH,
        event_id=event.event_id,
        event_type=event.event_type.value,
        timestamp=event.timestamp,
        details=event.details,
    )
    row = event.model_dump()
    assert AuditTrailRepository._compute_event_hash(row) == event.hash


@pytest.mark.asyncio
async def test_audit_save_and_retrieve(temp_db):
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

    # Chain linkage is valid (single event with correct previous_hash).
    # Hash recomputation will FAIL here because the stored "a"*64 doesn't
    # match the SHA-256 of the payload — that's expected in this smoke test
    # which only tests round-trip persistence, not hash authenticity.
    _ok, _msg = await repo.verify_integrity("sim-1")
    # We don't assert ok here; a separate integrity test covers that path.


@pytest.mark.asyncio
async def test_audit_integrity_checks(temp_db):
    from app.db.audit import AuditTrailRepository

    repo = AuditTrailRepository()

    # 1. Valid hash chain
    event1 = {
        "event_id": "ev-int-1",
        "simulation_id": "sim-int-1",
        "event_type": "turn",
        "timestamp": "2026-01-01",
        "actor": "sys",
        "details": {},
        "previous_hash": "0" * 64,
    }
    event1["hash"] = repo._compute_event_hash(event1)
    await repo.save_event(event1)

    ok, msg = await repo.verify_integrity("sim-int-1")
    assert ok is True

    # 2. Tampered payload / hash mismatch
    event_tamper = {
        "event_id": "ev-int-2",
        "simulation_id": "sim-int-tampered",
        "event_type": "turn",
        "timestamp": "2026-01-01",
        "actor": "sys",
        "details": {},
        "previous_hash": "0" * 64,
        "hash": "invalid_stored_hash_tampered_value",
    }
    await repo.save_event(event_tamper)
    ok, msg = await repo.verify_integrity("sim-int-tampered")
    assert ok is False
    assert "Invalid hash" in msg or "hash mismatch" in msg.lower() or "integrity" in msg.lower()

    # 3. Chain linkage broken
    event2 = {
        "event_id": "ev-int-3",
        "simulation_id": "sim-int-1",
        "event_type": "turn",
        "timestamp": "2026-01-02",
        "actor": "sys",
        "details": {},
        "previous_hash": "b" * 64,  # Intentionally broken linkage from ev-int-1
    }
    event2["hash"] = repo._compute_event_hash(event2)
    await repo.save_event(event2)

    ok, msg = await repo.verify_integrity("sim-int-1")
    assert ok is False


# ---------------------------------------------------------------------------
# ChatHistoryRepository (basic smoke test)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_save_and_retrieve(temp_db):
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


def test_flatten_chat_exchanges_interleaves_user_and_assistant():
    """Session replay must alternate user/assistant per exchange, not all users then all assistants."""
    from app.db.chat import flatten_chat_exchanges_to_session_messages

    rows = [
        {
            "id": "a",
            "simulation_id": "sim",
            "agent_id": "ag1",
            "agent_name": "A",
            "user_message": "u1",
            "agent_response": "a1",
            "timestamp": "t1",
        },
        {
            "id": "b",
            "simulation_id": "sim",
            "agent_id": "ag1",
            "agent_name": "A",
            "user_message": "u2",
            "agent_response": "a2",
            "timestamp": "t2",
        },
    ]
    flat = flatten_chat_exchanges_to_session_messages(rows)
    assert [m["content"] for m in flat] == ["u1", "a1", "u2", "a2"]
    assert [m["is_user"] for m in flat] == [True, False, True, False]


# ---------------------------------------------------------------------------
# AgentMemoryRepository (basic smoke test)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_memory_save_and_search(temp_db):
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
