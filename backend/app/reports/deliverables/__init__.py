"""Deliverable analysis helpers for report generation."""

from app.reports.deliverables.executive_summary import (
    extract_key_findings,
    format_for_presentation,
    rank_recommendations,
)
from app.reports.deliverables.risk_register import (
    extract_risk_signals,
    identify_risk_owner,
    score_risk_impact,
    score_risk_probability,
)
from app.reports.deliverables.scenario_matrix import (
    calculate_probability_ranges,
    construct_scenario_narratives,
    get_outcome_dimensions,
    identify_decision_branches,
)
from app.reports.deliverables.stakeholder_heatmap import (
    calculate_influence_scores,
    compute_support_levels,
    identify_key_concerns,
)

__all__ = [
    "extract_risk_signals",
    "score_risk_probability",
    "score_risk_impact",
    "identify_risk_owner",
    "identify_decision_branches",
    "construct_scenario_narratives",
    "calculate_probability_ranges",
    "get_outcome_dimensions",
    "compute_support_levels",
    "calculate_influence_scores",
    "identify_key_concerns",
    "extract_key_findings",
    "rank_recommendations",
    "format_for_presentation",
]
