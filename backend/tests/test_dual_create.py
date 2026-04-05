"""POST /api/simulations/dual-create: pair creation with rollback on second failure."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.simulation.engine import simulation_engine


def _minimal_payload(name: str = "A") -> dict:
    return {
        "name": name,
        "description": "",
        "playbook_id": None,
        "environment_type": "boardroom",
        "agents": [{"name": "CEO", "archetype_id": "ceo"}],
        "total_rounds": 3,
        "seed_ids": [],
        "parameters": {},
    }


def test_dual_create_success():
    with TestClient(app) as client:
        body = {
            "scenario_a": _minimal_payload("PairA"),
            "scenario_b": {
                **_minimal_payload("PairB"),
                "environment_type": "war_room",
            },
        }
        r = client.post("/api/simulations/dual-create", json=body)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["simulation_a"]["config"]["name"] == "PairA"
        assert j["simulation_b"]["config"]["name"] == "PairB"
        assert j["simulation_a"]["config"]["id"] != j["simulation_b"]["config"]["id"]


def test_dual_create_rolls_back_first_when_second_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    first_ids: list[str] = []
    orig = simulation_engine.create_simulation

    async def fake_create(config, graph_memory_manager=None, *, inference_router=None):
        if config.name == "FAIL_B":
            raise ValueError("intentional second failure")
        state = await orig(config, graph_memory_manager, inference_router=inference_router)
        first_ids.append(state.config.id)
        return state

    monkeypatch.setattr(simulation_engine, "create_simulation", fake_create)

    with TestClient(app) as client:
        body = {
            "scenario_a": _minimal_payload("OK_A"),
            "scenario_b": {**_minimal_payload("FAIL_B")},
        }
        r = client.post("/api/simulations/dual-create", json=body)
        assert r.status_code == 422, r.text
        assert "intentional" in str(r.json().get("detail", "")).lower()
        assert len(first_ids) == 1
        probe = client.get(f"/api/simulations/{first_ids[0]}")
        assert probe.status_code == 404


def test_dual_create_500_includes_failed_part_a(monkeypatch: pytest.MonkeyPatch):
    orig = simulation_engine.create_simulation

    async def fake_create(config, graph_memory_manager=None, *, inference_router=None):
        if config.name == "FAIL_A":
            raise RuntimeError("intentional A failure")
        return await orig(config, graph_memory_manager, inference_router=inference_router)

    monkeypatch.setattr(simulation_engine, "create_simulation", fake_create)

    with TestClient(app) as client:
        body = {
            "scenario_a": {**_minimal_payload("FAIL_A")},
            "scenario_b": _minimal_payload("OK_B"),
        }
        r = client.post("/api/simulations/dual-create", json=body)
        assert r.status_code == 500, r.text
        detail = str(r.json().get("detail", ""))
        assert "failed_part=A" in detail


def test_dual_create_500_includes_failed_part_b(monkeypatch: pytest.MonkeyPatch):
    orig = simulation_engine.create_simulation

    async def fake_create(config, graph_memory_manager=None, *, inference_router=None):
        if config.name == "FAIL_B":
            raise RuntimeError("intentional B failure")
        return await orig(config, graph_memory_manager, inference_router=inference_router)

    monkeypatch.setattr(simulation_engine, "create_simulation", fake_create)

    with TestClient(app) as client:
        body = {
            "scenario_a": _minimal_payload("OK_A"),
            "scenario_b": {**_minimal_payload("FAIL_B")},
        }
        r = client.post("/api/simulations/dual-create", json=body)
        assert r.status_code == 500, r.text
        detail = str(r.json().get("detail", ""))
        assert "failed_part=B" in detail
