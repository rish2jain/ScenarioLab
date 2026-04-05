"""Tests for risk impact_score × likelihood_score → categorical impact mapping."""

import pytest

from app.reports.report_agent import _risk_impact_level_from_dimension_scores


@pytest.mark.parametrize(
    ("is_", "ls", "expected"),
    [
        (1, 1, "low"),  # 1
        (2, 2, "low"),  # 4
        (1, 5, "low"),  # 5 — max product still in low band
        (2, 3, "medium"),  # 6
        (2, 5, "medium"),  # 10 — asymmetric, below high threshold
        (5, 2, "medium"),  # 10 — same product, swapped dimensions
        (3, 3, "medium"),  # 9
        (3, 4, "high"),  # 12
        (3, 5, "high"),  # 15 — asymmetric mid high band
        (4, 4, "high"),  # 16
        (4, 5, "critical"),  # 20
        (5, 5, "critical"),  # 25
    ],
)
def test_risk_impact_level_boundaries(is_: int, ls: int, expected: str) -> None:
    assert _risk_impact_level_from_dimension_scores(is_, ls) == expected


def test_risk_impact_level_clamps_inputs() -> None:
    # Out-of-range values clamp to 1–5 before multiplying (99→5, -3→1 → product 5 → low).
    assert _risk_impact_level_from_dimension_scores(99, -3) == "low"
