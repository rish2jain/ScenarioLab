"""Multi-scenario batch execution for side-by-side comparison."""

import logging
import time
import uuid

from pydantic import BaseModel

from app.analytics.analytics_agent import AnalyticsAgent, SimulationMetrics
from app.simulation.engine import SimulationEngine
from app.simulation.models import SimulationConfig
from app.simulation.monte_carlo import (
    MonteCarloConfig,
    MonteCarloResult,
    MonteCarloRunner,
)

logger = logging.getLogger(__name__)


class BatchScenario(BaseModel):
    """A single scenario in a batch execution."""
    id: str
    name: str
    config: SimulationConfig
    description: str = ""


class BatchConfig(BaseModel):
    """Configuration for batch execution of multiple scenarios."""
    scenarios: list[BatchScenario]
    monte_carlo_iterations: int = 0  # 0 = single run per scenario
    compare_metrics: list[str] = [
        "time_to_consensus",
        "policy_adoption_rate",
        "compliance_violation_rate",
    ]


class ScenarioComparison(BaseModel):
    """Comparison results across multiple scenarios."""
    scenarios: list[dict]  # [{id, name, metrics: SimulationMetrics}]
    comparative_summary: dict  # Side-by-side metric comparison
    best_scenario: str | None  # ID of best-performing scenario


class BatchRunner:
    """Execute multiple scenarios for side-by-side comparison."""

    def __init__(self, simulation_engine: SimulationEngine):
        self.engine = simulation_engine
        self.analytics_agent = AnalyticsAgent()
        self.monte_carlo_runner = MonteCarloRunner(simulation_engine)

    async def run_batch(
        self, config: BatchConfig, on_progress=None
    ) -> ScenarioComparison:
        """Run all scenarios and produce comparison."""
        logger.info(
            f"Starting batch run with {len(config.scenarios)} scenarios"
        )
        start_time = time.time()

        scenario_results: list[dict] = []

        for i, scenario in enumerate(config.scenarios):
            logger.info(
                f"Running scenario {i + 1}/{len(config.scenarios)}: "
                f"{scenario.name}"
            )

            try:
                if config.monte_carlo_iterations > 0:
                    # Run Monte Carlo for this scenario
                    mc_config = MonteCarloConfig(
                        base_config=scenario.config,
                        iterations=config.monte_carlo_iterations,
                    )
                    mc_result = await self.monte_carlo_runner.run(
                        mc_config,
                        on_progress=lambda p: on_progress({
                            "scenario": scenario.name,
                            "scenario_index": i + 1,
                            "total_scenarios": len(config.scenarios),
                            **p,
                        }) if on_progress else None,
                    )

                    # Aggregate metrics from Monte Carlo results
                    aggregated_metrics = self._aggregate_mc_metrics(
                        mc_result
                    )

                    scenario_results.append({
                        "id": scenario.id,
                        "name": scenario.name,
                        "description": scenario.description,
                        "metrics": aggregated_metrics,
                        "monte_carlo_result": mc_result,
                    })

                else:
                    # Single run
                    iter_config = scenario.config.model_copy()
                    iter_config.id = str(uuid.uuid4())

                    sim_state = await self.engine.create_simulation(
                        iter_config
                    )
                    await self.engine.run_simulation(sim_state.config.id)

                    final_state = await self.engine.get_simulation(
                        sim_state.config.id
                    )

                    if final_state and final_state.status.value == "completed":
                        aa = self.analytics_agent
                        metrics = await aa.analyze_simulation(final_state)

                        scenario_results.append({
                            "id": scenario.id,
                            "name": scenario.name,
                            "description": scenario.description,
                            "metrics": metrics,
                        })
                    else:
                        scenario_results.append({
                            "id": scenario.id,
                            "name": scenario.name,
                            "description": scenario.description,
                            "metrics": None,
                            "error": "Simulation did not complete",
                        })

                # Report progress
                if on_progress:
                    await on_progress({
                        "scenario_index": i + 1,
                        "total_scenarios": len(config.scenarios),
                        "percentage": round(
                            (i + 1) / len(config.scenarios) * 100, 1
                        ),
                        "current_scenario": scenario.name,
                    })

            except Exception as e:
                logger.error(f"Scenario {scenario.name} failed: {e}")
                scenario_results.append({
                    "id": scenario.id,
                    "name": scenario.name,
                    "description": scenario.description,
                    "metrics": None,
                    "error": str(e),
                })

        # Generate comparative summary
        comparative_summary = self.compare_scenarios(
            scenario_results, config.compare_metrics
        )

        # Determine best scenario
        best_scenario = self._determine_best_scenario(
            scenario_results, config.compare_metrics
        )

        total_duration = time.time() - start_time
        logger.info(
            f"Batch run complete in {total_duration:.1f}s. "
            f"Best scenario: {best_scenario}"
        )

        return ScenarioComparison(
            scenarios=scenario_results,
            comparative_summary=comparative_summary,
            best_scenario=best_scenario,
        )

    def _aggregate_mc_metrics(
        self, mc_result: MonteCarloResult
    ) -> SimulationMetrics:
        """Aggregate metrics from Monte Carlo results."""
        # Use confidence interval means as aggregated values
        ci = mc_result.confidence_intervals

        return SimulationMetrics(
            simulation_id=f"mc_aggregate_{mc_result.config.base_config.id}",
            compliance_violation_rate=ci.get(
                "compliance_violation_rate", {}
            ).get("mean", 0.0),
            time_to_consensus=None,  # Aggregate doesn't have single value
            sentiment_trajectory=[],  # Not aggregated
            role_polarization_index={},  # Not aggregated
            policy_adoption_rate=ci.get("policy_adoption_rate", {}).get(
                "mean", 0.0
            ),
            coalition_formation_events=[],
            key_turning_points=[],
            agent_activity_scores={},
            decision_outcomes=[],
        )

    def compare_scenarios(
        self,
        results: list[dict],
        compare_metrics: list[str],
    ) -> dict:
        """Generate comparative metrics across scenarios."""
        comparison = {
            "by_metric": {},
            "rankings": {},
            "summary": {},
        }

        # Compare by each metric
        for metric in compare_metrics:
            metric_values = []

            for result in results:
                metrics = result.get("metrics")
                if metrics:
                    value = getattr(metrics, metric, None)
                    if value is not None:
                        metric_values.append({
                            "scenario_id": result["id"],
                            "scenario_name": result["name"],
                            "value": value,
                        })

            if metric_values:
                # Sort by value (lower is better for time, violations)
                sorted_values = sorted(
                    metric_values, key=lambda x: x["value"]
                )

                comparison["by_metric"][metric] = {
                    "values": metric_values,
                    "best": sorted_values[0] if sorted_values else None,
                    "worst": sorted_values[-1] if sorted_values else None,
                    "range": {
                        "min": min(v["value"] for v in metric_values),
                        "max": max(v["value"] for v in metric_values),
                    },
                }

                # Create rankings
                for rank, item in enumerate(sorted_values, 1):
                    if item["scenario_id"] not in comparison["rankings"]:
                        comparison["rankings"][item["scenario_id"]] = {}
                    comparison["rankings"][item["scenario_id"]][metric] = rank

        # Overall summary
        successful_runs = sum(
            1 for r in results if r.get("metrics") is not None
        )
        comparison["summary"] = {
            "total_scenarios": len(results),
            "successful_runs": successful_runs,
            "failed_runs": len(results) - successful_runs,
        }

        return comparison

    def _determine_best_scenario(
        self,
        results: list[dict],
        compare_metrics: list[str],
    ) -> str | None:
        """Determine the best performing scenario."""
        # Score each scenario based on rankings
        scenario_scores: dict[str, float] = {}

        for metric in compare_metrics:
            metric_values = []

            for result in results:
                metrics = result.get("metrics")
                if metrics:
                    value = getattr(metrics, metric, None)
                    if value is not None:
                        metric_values.append({
                            "scenario_id": result["id"],
                            "value": value,
                        })

            if metric_values:
                # Sort by value (lower is better)
                sorted_values = sorted(
                    metric_values, key=lambda x: x["value"]
                )

                # Assign scores (inverse rank)
                n = len(sorted_values)
                for rank, item in enumerate(sorted_values, 1):
                    scenario_id = item["scenario_id"]
                    if scenario_id not in scenario_scores:
                        scenario_scores[scenario_id] = 0
                    # Higher score for better rank
                    scenario_scores[scenario_id] += (n - rank + 1) / n

        if not scenario_scores:
            return None

        # Return scenario with highest score
        return max(scenario_scores, key=scenario_scores.get)
