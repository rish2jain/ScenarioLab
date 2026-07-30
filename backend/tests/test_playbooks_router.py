"""HTTP smoke tests for playbooks router (TestClient, no LLM)."""

from fastapi.testclient import TestClient

from app.main import app


def test_list_playbooks():
    with TestClient(app) as client:
        r = client.get("/api/playbooks")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 1
    assert len(body["playbooks"]) == body["count"]
    assert any(p["id"] == "boardroom-rehearsal" for p in body["playbooks"])


def test_get_playbook_detail():
    with TestClient(app) as client:
        r = client.get("/api/playbooks/boardroom-rehearsal")
    assert r.status_code == 200
    playbook = r.json()["playbook"]
    assert playbook["id"] == "boardroom-rehearsal"
    assert playbook["agent_roster"]


def test_get_playbook_404():
    with TestClient(app) as client:
        r = client.get("/api/playbooks/not-a-real-playbook")
    assert r.status_code == 404


def test_get_playbook_roster():
    with TestClient(app) as client:
        r = client.get("/api/playbooks/boardroom-rehearsal/roster")
    assert r.status_code == 200
    body = r.json()
    assert body["playbook_id"] == "boardroom-rehearsal"
    assert len(body["roster"]) >= 1


def test_validate_endpoint_rejects_empty_config():
    with TestClient(app) as client:
        r = client.post("/api/playbooks/validate", json={"config": {}})
    assert r.status_code == 200
    body = r.json()
    assert body["is_valid"] is False
    assert len(body["errors"]) >= 1
