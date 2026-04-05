"""Monte Carlo convergence uses policy_adoption_rate from iteration metrics_summary."""

from typing import Any

from app.simulation.models import SimulationConfig
from app.simulation.monte_carlo import (
    MonteCarloRunner,
    _policy_adoption_rates_from_iterations,
)


class _UnusedMonteCarloEngine:
    """Minimal engine stand-in; convergence tests only use ``check_convergence``."""

    async def create_simulation(
        self,
        config: SimulationConfig,
        graph_memory_manager: Any = None,
        *,
        inference_router: Any = None,
    ) -> Any:
        raise RuntimeError("unused in this test")

    async def run_simulation(self, simulation_id: str, on_message: Any = None) -> Any:
        raise RuntimeError("unused in this test")

    def get_agent_router(self, sim_id: str, agent_index: int = 0) -> Any:
        return None

    async def get_simulation(self, simulation_id: str) -> Any:
        return None

    async def delete_simulation(self, simulation_id: str) -> bool:
        return True


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
    runner = MonteCarloRunner(_UnusedMonteCarloEngine())
    # 10 values near 0.5 — recent mean ~= overall mean
    vals = [0.48 + i * 0.001 for i in range(10)]
    assert runner.check_convergence(vals, threshold=0.05) is True


def test_check_convergence_false_short_series() -> None:
    runner = MonteCarloRunner(_UnusedMonteCarloEngine())
    assert runner.check_convergence([0.5, 0.5], threshold=0.05) is False
