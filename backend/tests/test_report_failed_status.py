"""Report generation failures must not be reported as draft."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.reports.models import SimulationReport
from app.reports.report_agent import ReportAgent
from app.simulation.models import (
    EnvironmentType,
    SimulationConfig,
    SimulationState,
    SimulationStatus,
)


@pytest.mark.asyncio
async def test_generate_full_report_sets_failed_on_exception():
    sim = SimulationState(
        config=SimulationConfig(
            id="sim-report-fail",
            name="Failing report sim",
            playbook_id=None,
            environment_type=EnvironmentType.BOARDROOM,
            agents=[],
            total_rounds=1,
        ),
        status=SimulationStatus.COMPLETED,
        agents=[],
    )
    llm = MagicMock()
    agent = ReportAgent(llm, sim)
    agent.generate_objective_assessment = AsyncMock(side_effect=RuntimeError("boom"))
    agent.generate_executive_summary = AsyncMock(return_value=None)
    agent.generate_risk_register = AsyncMock(return_value=None)
    agent.generate_scenario_matrix = AsyncMock(return_value=None)
    agent.generate_stakeholder_heatmap = AsyncMock(return_value=None)
    agent._memory_tool_context = AsyncMock(return_value=None)
    agent.collect_tool_context = MagicMock(return_value=None)
    agent.tool_audit_round_summary = MagicMock(return_value=[])

    report = await agent.generate_full_report()

    assert isinstance(report, SimulationReport)
    assert report.status == "failed"
