"""Dual-run preset endpoint: shared batch id and JSON-safe payloads."""

from fastapi.testclient import TestClient

from app.main import app
from app.simulation.engine import simulation_engine


def test_dual_run_preset_invalid_environment_type_b_emits_structured_warning():
    client = TestClient(app)
    r = client.post(
        "/api/simulations/dual-run-preset",
        json={
            "name_a": "Scenario A",
            "name_b": "Scenario B",
            "base": {
                "name": "Comparison base",
                "description": "",
                "playbook_id": None,
                "environment_type": "boardroom",
                "agents": [{"name": "CEO", "archetype_id": "ceo"}],
                "total_rounds": 5,
                "seed_ids": [],
                "parameters": {},
            },
            "environment_type_b": "not_a_valid_env",
        },
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert len(j["warnings"]) == 1
    w = j["warnings"][0]
    assert w["code"] == "invalid_environment_type_b"
    assert "not_a_valid_env" in (w.get("message") or "")
    assert w["metadata"]["field"] == "environment_type_b"
    assert w["metadata"]["value"] == "not_a_valid_env"


def test_dual_run_preset_merges_batch_parent_id_and_json_safe():
    client = TestClient(app)
    r = client.post(
        "/api/simulations/dual-run-preset",
        json={
            "name_a": "Scenario A",
            "name_b": "Scenario B",
            "base": {
                "name": "Comparison base",
                "description": "",
                "playbook_id": None,
                "environment_type": "boardroom",
                "agents": [{"name": "CEO", "archetype_id": "ceo"}],
                "total_rounds": 5,
                "seed_ids": [],
                "parameters": {"foo": 1},
            },
            "environment_type_b": "war_room",
        },
    )
    assert r.status_code == 200, r.text
    j = r.json()
    bid = j["batch_parent_id"]
    assert isinstance(bid, str) and len(bid) >= 8
    assert j["scenario_a"]["parameters"]["batch_parent_id"] == bid
    assert j["scenario_b"]["parameters"]["batch_parent_id"] == bid
    assert j["scenario_a"]["parameters"]["foo"] == 1
    assert j["scenario_a"]["environment_type"] == "boardroom"
    assert j["scenario_b"]["environment_type"] == "war_room"
    assert j["scenario_a"]["name"] == "Scenario A"
    assert j["scenario_b"]["name"] == "Scenario B"


def test_dual_run_preset_create_creates_pair_and_matches_batch_id():
    with TestClient(app) as client:
        r = client.post(
            "/api/simulations/dual-run-preset-create",
            json={
                "name_a": "Run A",
                "name_b": "Run B",
                "base": {
                    "name": "Comparison base",
                    "description": "",
                    "playbook_id": None,
                    "environment_type": "boardroom",
                    "agents": [{"name": "CEO", "archetype_id": "ceo"}],
                    "total_rounds": 5,
                    "seed_ids": [],
                    "parameters": {},
                },
                "environment_type_b": "war_room",
            },
        )
    assert r.status_code == 200, r.text
    j = r.json()
    bid = j["batch_parent_id"]
    assert isinstance(bid, str) and len(bid) >= 8
    assert j["simulation_a"]["config"]["parameters"]["batch_parent_id"] == bid
    assert j["simulation_b"]["config"]["parameters"]["batch_parent_id"] == bid
    assert j["simulation_a"]["config"]["name"] == "Run A"
    assert j["simulation_b"]["config"]["name"] == "Run B"
    assert j["simulation_a"]["config"]["id"] != j["simulation_b"]["config"]["id"]


def test_dual_run_preset_create_rolls_back_when_second_fails(monkeypatch):
    first_ids: list[str] = []
    orig = simulation_engine.create_simulation

    async def fake_create(config, graph_memory_manager=None):
        if config.name == "FAIL_B":
            raise ValueError("intentional second failure")
        state = await orig(config, graph_memory_manager)
        first_ids.append(state.config.id)
        return state

    monkeypatch.setattr(simulation_engine, "create_simulation", fake_create)

    with TestClient(app) as client:
        r = client.post(
            "/api/simulations/dual-run-preset-create",
            json={
                "name_a": "OK_A",
                "name_b": "FAIL_B",
                "base": {
                    "name": "Comparison base",
                    "description": "",
                    "playbook_id": None,
                    "environment_type": "boardroom",
                    "agents": [{"name": "CEO", "archetype_id": "ceo"}],
                    "total_rounds": 3,
                    "seed_ids": [],
                    "parameters": {},
                },
            },
        )
        assert r.status_code == 422, r.text
        assert "intentional" in str(r.json().get("detail", "")).lower()
        assert len(first_ids) == 1
        probe = client.get(f"/api/simulations/{first_ids[0]}")
        assert probe.status_code == 404
