"""Report Generation module for ScenarioLab.

This module provides consulting-grade report generation from simulation
results, including executive summaries, risk registers, scenario matrices,
and stakeholder heatmaps.
"""

from app.reports.models import (
    ExecutiveSummary,
    KeyRecommendation,
    ReviewCheckpoint,
    RiskItem,
    RiskRegister,
    ScenarioMatrix,
    ScenarioOutcome,
    SimulationReport,
    StakeholderHeatmap,
    StakeholderPosition,
)
from app.reports.report_agent import ReportAgent

__all__ = [
    "RiskItem",
    "RiskRegister",
    "ScenarioOutcome",
    "ScenarioMatrix",
    "StakeholderPosition",
    "StakeholderHeatmap",
    "KeyRecommendation",
    "ExecutiveSummary",
    "ReviewCheckpoint",
    "SimulationReport",
    "ReportAgent",
]
