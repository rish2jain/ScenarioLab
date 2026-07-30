"""Pagination smoke tests for GET /api/simulations and GET /api/reports."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.reports import router as reports_router
from app.reports.models import SimulationReport
from app.simulation.engine import simulation_engine


def _report(rid: str, name: str, updated: str) -> SimulationReport:
    return SimulationReport(
        id=rid,
        simulation_id=f"sim-{rid}",
        simulation_name=name,
        created_at=updated,
        updated_at=updated,
    )


def test_list_simulations_pagination_keys_and_slice():
    items = [
        {
            "id": f"sim-{i}",
            "name": f"Sim {i}",
            "status": "completed",
            "updated_at": datetime(2024, 1, i + 1, tzinfo=timezone.utc).isoformat(),
        }
        for i in range(5)
    ]
    with (
        patch.object(
            simulation_engine,
            "list_simulations",
            new=AsyncMock(
                return_value={
                    "items": items[2:4],
                    "total": 5,
                    "limit": 2,
                    "offset": 2,
                }
            ),
        ),
        TestClient(app) as client,
    ):
        r = client.get("/api/simulations?limit=2&offset=2")

    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 5
    assert body["limit"] == 2
    assert body["offset"] == 2
    assert len(body["items"]) == 2
    assert body["items"][0]["id"] == "sim-2"


def test_list_simulations_forwards_query_params():
    mock = AsyncMock(return_value={"items": [], "total": 0, "limit": 10, "offset": 5})
    with (
        patch.object(simulation_engine, "list_simulations", new=mock),
        TestClient(app) as client,
    ):
        r = client.get("/api/simulations?limit=10&offset=5")

    assert r.status_code == 200
    mock.assert_awaited_once()
    kwargs = mock.await_args.kwargs
    assert kwargs["limit"] == 10
    assert kwargs["offset"] == 5


def test_list_reports_pagination_from_store():
    reports = {
        "r1": _report("r1", "A", "2024-01-03T00:00:00+00:00"),
        "r2": _report("r2", "B", "2024-01-02T00:00:00+00:00"),
        "r3": _report("r3", "C", "2024-01-01T00:00:00+00:00"),
    }
    with (
        patch.dict(reports_router._report_store, reports, clear=True),
        patch.object(
            reports_router._report_repo,
            "list_page",
            new=AsyncMock(return_value=([], 0)),
        ),
        TestClient(app) as client,
    ):
        r = client.get("/api/reports?limit=2&offset=1")

    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert len(body["items"]) == 2
    # Sorted by updated_at desc: r1, r2, r3 → offset 1 → r2, r3
    assert body["items"][0]["id"] == "r2"
    assert body["items"][1]["id"] == "r3"


def test_list_reports_rejects_invalid_limit():
    with TestClient(app) as client:
        r = client.get("/api/reports?limit=0")
    assert r.status_code == 422
