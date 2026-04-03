"""Tests for the SQLite persistence layer."""

from unittest.mock import patch

import pytest

from app.simulation.models import (
    AgentConfig,
    EnvironmentType,
    SimulationConfig,
    SimulationState,
    SimulationStatus,
)


@pytest.fixture
def sim_config():
    return SimulationConfig(
        name="Test Sim",
        description="A test",
        environment_type=EnvironmentType.BOARDROOM,
        agents=[AgentConfig(name="CEO", archetype_id="ceo")],
        total_rounds=5,
    )


@pytest.fixture
def sim_state(sim_config):
    return SimulationState(
        config=sim_config,
        status=SimulationStatus.READY,
    )


@pytest.fixture
async def repo(tmp_path):
    """Initialize a test database and return a SimulationRepository."""
    import app.database as db_mod

    db_path = tmp_path / "test.db"
    # Patch the module-level path so init_database() uses our temp dir
    with (
        patch.object(db_mod, "_DB_DIR", tmp_path),
        patch.object(db_mod, "_DB_PATH", db_path),
    ):
        await db_mod.init_database()
        from app.database import SimulationRepository

        yield SimulationRepository()
        await db_mod.close_database()


@pytest.mark.asyncio
class TestSimulationRepository:
    async def test_save_and_get(self, repo, sim_state):
        await repo.save(sim_state)

        loaded = await repo.get(sim_state.config.id)
        assert loaded is not None
        assert loaded.config.id == sim_state.config.id
        assert loaded.config.name == "Test Sim"
        assert loaded.status == SimulationStatus.READY

    async def test_get_nonexistent(self, repo):
        result = await repo.get("nonexistent-id")
        assert result is None

    async def test_list_all(self, repo, sim_config):
        for i in range(3):
            config = sim_config.model_copy(
                update={"id": f"sim-{i}", "name": f"Sim {i}"}
            )
            state = SimulationState(
                config=config, status=SimulationStatus.READY
            )
            await repo.save(state)

        summaries = await repo.list_all()
        assert len(summaries) == 3

    async def test_delete(self, repo, sim_state):
        await repo.save(sim_state)

        deleted = await repo.delete(sim_state.config.id)
        assert deleted is True

        loaded = await repo.get(sim_state.config.id)
        assert loaded is None

    async def test_delete_nonexistent(self, repo):
        deleted = await repo.delete("nonexistent")
        assert deleted is False

    async def test_update_status(self, repo, sim_state):
        await repo.save(sim_state)

        await repo.update_status(sim_state.config.id, "running")

        loaded = await repo.get(sim_state.config.id)
        assert loaded is not None
        assert loaded.status == SimulationStatus.RUNNING

    async def test_upsert_overwrites(self, repo, sim_state):
        await repo.save(sim_state)

        sim_state.status = SimulationStatus.COMPLETED
        sim_state.current_round = 5
        await repo.save(sim_state)

        loaded = await repo.get(sim_state.config.id)
        assert loaded is not None
        assert loaded.status == SimulationStatus.COMPLETED
        assert loaded.current_round == 5
