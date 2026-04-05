"""Tests for reports router GET vs POST semantics."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.reports import router as reports_router
from app.reports.models import SimulationReport
from app.simulation.models import (
    EnvironmentType,
    SimulationConfig,
    SimulationState,
    SimulationStatus,
)


def _minimal_completed_state(simulation_id: str = "sim-test") -> SimulationState:
    cfg = SimulationConfig(
        id=simulation_id,
        name="Test",
        playbook_id="p1",
        environment_type=EnvironmentType.BOARDROOM,
        agents=[],
    )
    return SimulationState(
        config=cfg,
        status=SimulationStatus.COMPLETED,
    )


def test_get_report_missing_returns_404_without_implicit_generation():
    """GET uses generate_if_missing=False — 404 when no report exists (public route)."""
    with (
        patch.dict(reports_router._report_store, {}, clear=True),
        patch.object(
            reports_router._report_repo,
            "get_by_simulation",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            reports_router.simulation_engine,
            "get_simulation",
            new=AsyncMock(return_value=_minimal_completed_state()),
        ),
        TestClient(app) as client,
    ):
        response = client.get("/api/simulations/sim-test/report")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_post_report_returns_201_when_newly_generated():
    """POST creates a report — 201 Created."""
    new_report = SimulationReport(
        id="rep-new",
        simulation_id="sim-test",
        simulation_name="Test",
    )
    mock_agent = MagicMock()
    mock_agent.generate_full_report = AsyncMock(return_value=new_report)
    with (
        patch.dict(reports_router._report_store, {}, clear=True),
        patch.object(
            reports_router._report_repo,
            "get_by_simulation",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            reports_router._report_repo,
            "save",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            reports_router.simulation_engine,
            "get_simulation",
            new=AsyncMock(return_value=_minimal_completed_state()),
        ),
        patch.object(
            reports_router,
            "get_llm_provider",
            return_value=MagicMock(),
        ),
        patch.object(reports_router, "ReportAgent", return_value=mock_agent),
        TestClient(app) as client,
    ):
        response = client.post("/api/simulations/sim-test/report")

    assert response.status_code == 201
    assert response.json()["id"] == "rep-new"


def test_post_report_returns_200_when_existing_idempotent():
    """POST returns stored report — 200 OK (idempotent)."""
    existing = SimulationReport(
        id="rep-existing",
        simulation_id="sim-test",
        simulation_name="Test",
    )
    with (
        patch.dict(
            reports_router._report_store,
            {existing.id: existing},
            clear=True,
        ),
        patch.object(
            reports_router.simulation_engine,
            "get_simulation",
            new=AsyncMock(return_value=_minimal_completed_state()),
        ),
        patch.object(reports_router, "ReportAgent") as mock_ra,
        TestClient(app) as client,
    ):
        response = client.post("/api/simulations/sim-test/report")

    assert response.status_code == 200
    assert response.json()["id"] == "rep-existing"
    mock_ra.assert_not_called()


def test_dashboard_stats_reports_generated_matches_report_store():
    """GET /api/stats reportsGenerated counts stored reports, not completed sims."""
    mock_sims = [
        {"id": "a", "status": "completed"},
        {"id": "b", "status": "completed"},
    ]
    fake_report = MagicMock()
    with (
        patch.object(
            reports_router.simulation_engine,
            "list_simulations",
            new=AsyncMock(return_value=mock_sims),
        ),
        patch.dict(
            reports_router._report_store,
            {"r1": fake_report},
            clear=True,
        ),
        TestClient(app) as client,
    ):
        response = client.get("/api/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["reportsGenerated"] == 1
    assert body["totalSimulations"] == 2
