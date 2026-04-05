"""Monte Carlo batch runner for statistical confidence."""

import logging
import math
import random
import time
import uuid
from typing import Any, Protocol

from pydantic import BaseModel

from app.analytics.analytics_agent import AnalyticsAgent, SimulationMetrics
from app.config import settings
from app.inference_modes import InferenceMode, normalize_inference_mode
from app.simulation.models import SimulationConfig

logger = logging.getLogger(__name__)


class MonteCarloSimulationEngine(Protocol):
    """Async simulation API surface used by :class:`MonteCarloRunner.run`."""

    async def create_simulation(
        self,
        config: SimulationConfig,
        graph_memory_manager: Any = None,
        *,
        inference_router: Any = None,
    ) -> Any: ...

    async def run_simulation(self, simulation_id: str, on_message: Any = None) -> Any: ...

    def get_agent_router(self, sim_id: str, agent_index: int = 0) -> Any: ...

    async def get_simulation(self, simulation_id: str) -> Any: ...

    async def delete_simulation(self, simulation_id: str) -> bool: ...


def _policy_adoption_rates_from_iterations(
    iteration_results: list[dict],
) -> list[float]:
    """Collect policy adoption rates from MC iteration rows (supports nested metrics_summary)."""
    rates: list[float] = []
    for r in iteration_results:
        if r.get("status") != "completed":
            continue
        ms = r.get("metrics_summary")
        val = None
        if isinstance(ms, dict) and "policy_adoption_rate" in ms:
            val = ms.get("policy_adoption_rate")
        elif "policy_adoption_rate" in r:
            val = r.get("policy_adoption_rate")
        if val is not None:
            rates.append(float(val))
    return rates


class MonteCarloConfig(BaseModel):
    """Configuration for Monte Carlo simulation runs."""

    base_config: SimulationConfig
    iterations: int = 20  # 20-50 runs
    # Parameters to vary between runs
    variation_parameters: dict = {}
    # LLM temperature variation
    temperature_range: tuple[float, float] = (0.5, 0.9)


class MonteCarloResult(BaseModel):
    """Results from a Monte Carlo simulation run."""

    config: MonteCarloConfig
    iterations_completed: int
    results: list[dict]  # Summary per iteration
    confidence_intervals: dict  # {metric: {mean, std, ci_lower, ci_upper}}
    convergence_achieved: bool
    total_duration_seconds: float


class MonteCarloRunner:
    """Run multiple simulation iterations for statistical confidence."""

    def __init__(self, simulation_engine: MonteCarloSimulationEngine):
        self.engine = simulation_engine
        self.analytics_agent = AnalyticsAgent()

    async def run(self, config: MonteCarloConfig, on_progress=None) -> MonteCarloResult:
        """Run Monte Carlo iterations."""
        logger.info(f"Starting Monte Carlo run with {config.iterations} iterations")
        start_time = time.time()

        all_metrics: list[SimulationMetrics] = []
        iteration_results: list[dict] = []

        bp = config.base_config.parameters or {}
        inf_mode = normalize_inference_mode(bp.get("inference_mode") or settings.inference_mode)
        mc_hybrid_followup = inf_mode == InferenceMode.HYBRID.value and config.iterations > 1
        follow_up_router = None

        for i in range(config.iterations):
            iteration_start = time.time()
            logger.info(f"Monte Carlo iteration {i + 1}/{config.iterations}")

            sim_id = None
            try:
                # Create varied config for this iteration
                iter_config = self._create_varied_config(config.base_config, i, config)

                # Run simulation (iterations 2+ reuse copy-1 exemplars in hybrid mode)
                sim_state = await self.engine.create_simulation(
                    iter_config,
                    inference_router=follow_up_router if i > 0 else None,
                )
                sim_id = sim_state.config.id
                await self.engine.run_simulation(sim_id)

                if i == 0 and mc_hybrid_followup:
                    router = self.engine.get_agent_router(sim_id)
                    if router is not None and router.mode == InferenceMode.HYBRID.value:
                        follow_up_router = router.with_preloaded_exemplars()

                # Get final state
                final_state = await self.engine.get_simulation(sim_id)

                if final_state and final_state.status.value == "completed":
                    # Analyze with analytics agent
                    metrics = await self.analytics_agent.analyze_simulation(final_state)
                    all_metrics.append(metrics)

                    iteration_results.append(
                        {
                            "iteration": i + 1,
                            "simulation_id": sim_id,
                            "status": "completed",
                            "duration_seconds": time.time() - iteration_start,
                            "metrics_summary": {
                                "compliance_violation_rate": (metrics.compliance_violation_rate),
                                "time_to_consensus": metrics.time_to_consensus,
                                "policy_adoption_rate": (metrics.policy_adoption_rate),
                            },
                        }
                    )
                else:
                    iteration_results.append(
                        {
                            "iteration": i + 1,
                            "simulation_id": sim_id,
                            "status": "failed",
                            "duration_seconds": time.time() - iteration_start,
                            "error": "Simulation did not complete",
                        }
                    )

                # Report progress
                if on_progress:
                    await on_progress(
                        {
                            "iteration": i + 1,
                            "total": config.iterations,
                            "percentage": round((i + 1) / config.iterations * 100, 1),
                        }
                    )

            except Exception as e:
                logger.error(f"Iteration {i + 1} failed: {e}")
                iteration_results.append(
                    {
                        "iteration": i + 1,
                        "status": "error",
                        "error": str(e),
                    }
                )
            finally:
                # Clean up child simulation to prevent memory bloat
                if sim_id is not None:
                    try:
                        await self.engine.delete_simulation(sim_id)
                    except Exception as cleanup_err:
                        logger.warning(f"Failed to clean up simulation {sim_id}: " f"{cleanup_err}")

        # Compute confidence intervals
        confidence_intervals = self.compute_confidence_intervals(all_metrics)

        # Check convergence (metrics live under metrics_summary per iteration)
        convergence_achieved = self.check_convergence(_policy_adoption_rates_from_iterations(iteration_results))

        total_duration = time.time() - start_time

        result = MonteCarloResult(
            config=config,
            iterations_completed=len(all_metrics),
            results=iteration_results,
            confidence_intervals=confidence_intervals,
            convergence_achieved=convergence_achieved,
            total_duration_seconds=total_duration,
        )

        logger.info(
            f"Monte Carlo run complete: {len(all_metrics)}/" f"{config.iterations} successful in {total_duration:.1f}s"
        )
        return result

    def _create_varied_config(
        self,
        base_config: SimulationConfig,
        iteration: int,
        mc_config: MonteCarloConfig,
    ) -> SimulationConfig:
        """Create a varied configuration for a specific iteration."""
        # Deep copy base config
        config_dict = base_config.model_dump()

        # Add iteration-specific ID
        config_dict["id"] = str(uuid.uuid4())
        config_dict["name"] = f"{base_config.name} (MC Run {iteration + 1})"

        # Apply parameter variations
        if mc_config.variation_parameters:
            for param, variation in mc_config.variation_parameters.items():
                if param in config_dict:
                    if isinstance(variation, list):
                        # Cycle through list values
                        config_dict[param] = variation[iteration % len(variation)]
                    elif isinstance(variation, dict):
                        # Random variation within range
                        min_val = variation.get("min", 0)
                        max_val = variation.get("max", 1)
                        config_dict[param] = random.uniform(min_val, max_val)

        # Vary temperature if applicable (for LLM randomness)
        if "parameters" not in config_dict:
            config_dict["parameters"] = {}

        temp_range = mc_config.temperature_range
        config_dict["parameters"]["temperature"] = random.uniform(temp_range[0], temp_range[1])

        return SimulationConfig(**config_dict)

    def compute_confidence_intervals(self, all_metrics: list[SimulationMetrics]) -> dict:
        """Compute mean, std, 95% CI for each metric across runs."""
        if not all_metrics:
            return {}

        intervals = {}

        # Metrics to analyze
        metric_names = [
            "compliance_violation_rate",
            "policy_adoption_rate",
            "time_to_consensus",
        ]

        for metric_name in metric_names:
            values = []
            for m in all_metrics:
                val = getattr(m, metric_name)
                if val is not None:
                    values.append(float(val))

            if not values:
                continue

            # Compute statistics manually (no numpy)
            n = len(values)
            mean = sum(values) / n

            # Standard deviation
            variance = sum((x - mean) ** 2 for x in values) / n
            std = math.sqrt(variance)

            # 95% confidence interval (using t-distribution approximation)
            # For large n, t ~ 1.96; for small n, use 2.0 as conservative
            t_value = 2.0 if n < 30 else 1.96
            margin = t_value * (std / math.sqrt(n))

            intervals[metric_name] = {
                "mean": round(mean, 2),
                "std": round(std, 2),
                "ci_lower": round(max(mean - margin, 0), 2),
                "ci_upper": round(mean + margin, 2),
                "n": n,
            }

        return intervals

    def check_convergence(self, running_means: list[float], threshold: float = 0.05) -> bool:
        """Check if results have converged."""
        if len(running_means) < 10:
            return False

        # Check if the last 20% of values are within threshold of overall mean
        n = len(running_means)
        recent_start = int(n * 0.8)
        recent_values = running_means[recent_start:]

        if not recent_values:
            return False

        overall_mean = sum(running_means) / len(running_means)
        recent_mean = sum(recent_values) / len(recent_values)

        # Relative change
        if overall_mean == 0:
            return recent_mean == 0

        relative_change = abs(recent_mean - overall_mean) / overall_mean
        return relative_change < threshold
