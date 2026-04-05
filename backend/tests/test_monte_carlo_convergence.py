"""Monte Carlo convergence uses policy_adoption_rate from iteration metrics_summary."""

from app.simulation.engine import SimulationEngine
from app.simulation.monte_carlo import (
    MonteCarloRunner,
    _policy_adoption_rates_from_iterations,
)


def test_policy_adoption_rates_reads_metrics_summary() -> None:
    rows = [
        {
            "iteration": 1,
            "status": "completed",
            "metrics_summary": {"policy_adoption_rate": 0.5},
        },
        {
            "iteration": 2,
            "status": "completed",
            "metrics_summary": {"policy_adoption_rate": 0.52},
        },
    ]
    assert _policy_adoption_rates_from_iterations(rows) == [0.5, 0.52]


def test_policy_adoption_rates_legacy_top_level() -> None:
    rows = [
        {"status": "completed", "policy_adoption_rate": 0.4},
    ]
    assert _policy_adoption_rates_from_iterations(rows) == [0.4]


def test_policy_adoption_rates_skips_failed_iterations() -> None:
    rows = [
        {"status": "completed", "metrics_summary": {"policy_adoption_rate": 0.1}},
        {"status": "failed", "metrics_summary": {"policy_adoption_rate": 0.99}},
    ]
    assert _policy_adoption_rates_from_iterations(rows) == [0.1]


def test_check_convergence_true_when_stable_tail() -> None:
    runner = MonteCarloRunner(SimulationEngine())  # type: ignore[arg-type]
    # 10 values near 0.5 — recent mean ~= overall mean
    vals = [0.48 + i * 0.001 for i in range(10)]
    assert runner.check_convergence(vals, threshold=0.05) is True


def test_check_convergence_false_short_series() -> None:
    runner = MonteCarloRunner(SimulationEngine())  # type: ignore[arg-type]
    assert runner.check_convergence([0.5, 0.5], threshold=0.05) is False
