"""Tests for risk impact_score × likelihood_score → categorical impact mapping."""

import pytest

from app.reports.report_agent import _risk_impact_level_from_dimension_scores


@pytest.mark.parametrize(
    ("is_", "ls", "expected"),
    [
        (1, 1, "low"),  # 1
        (2, 2, "low"),  # 4
        (2, 3, "medium"),  # 6
        (3, 3, "medium"),  # 9
        (3, 4, "high"),  # 12
        (4, 4, "high"),  # 16
        (4, 5, "critical"),  # 20
        (5, 5, "critical"),  # 25
    ],
)
def test_risk_impact_level_boundaries(is_: int, ls: int, expected: str) -> None:
    assert _risk_impact_level_from_dimension_scores(is_, ls) == expected


def test_risk_impact_level_clamps_inputs() -> None:
    assert _risk_impact_level_from_dimension_scores(99, -3) == _risk_impact_level_from_dimension_scores(5, 1)
