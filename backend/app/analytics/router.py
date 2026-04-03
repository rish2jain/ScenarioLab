"""FastAPI router for analytics endpoints."""

import logging

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel

from app.analytics.analytics_agent import AnalyticsAgent
from app.analytics.cross_simulation import cross_simulation_learner
from app.analytics.fairness import FairnessAuditor, FairnessReport
from app.analytics.metrics_export import MetricsExporter
from app.analytics.shapley import AttributionResult, ShapleyAnalyzer
from app.cost_estimator import CostEstimate, CostEstimator
from app.llm.factory import get_llm_provider
from app.simulation.batch import BatchConfig, BatchRunner
from app.simulation.engine import simulation_engine
from app.simulation.monte_carlo import MonteCarloConfig, MonteCarloRunner

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analytics"])

# Initialize components
analytics_agent = AnalyticsAgent()
metrics_exporter = MetricsExporter()
cost_estimator = CostEstimator()
monte_carlo_runner = MonteCarloRunner(simulation_engine)
batch_runner = BatchRunner(simulation_engine)


class CostEstimateRequest(BaseModel):
    """Request for cost estimation."""
    agent_count: int
    rounds: int
    monte_carlo_iterations: int = 1
    provider: str = "openai"


class BatchCostEstimateRequest(BaseModel):
    """Request for batch cost estimation."""
    scenario_count: int
    agent_count: int
    rounds: int
    monte_carlo_iterations: int = 0
    provider: str = "openai"


class AttributionRequest(BaseModel):
    """Request for outcome attribution."""
    outcome_metric: str = "overall_outcome"


class FairnessAuditRequest(BaseModel):
    """Request for fairness audit."""
    perturbation_type: str = "gender"


@router.get("/simulations/{simulation_id}/analytics")
async def get_simulation_analytics(simulation_id: str):
    """Get analytics for a completed simulation."""
    logger.info(f"Getting analytics for simulation: {simulation_id}")

    # Get simulation state
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(
            status_code=404,
            detail=f"Simulation not found: {simulation_id}"
        )

    # Check if simulation is completed
    if sim_state.status.value not in ["completed", "failed"]:
        status = sim_state.status.value
        raise HTTPException(
            status_code=400,
            detail=f"Simulation not completed yet. Status: {status}"
        )

    try:
        # Run analytics
        metrics = await analytics_agent.analyze_simulation(sim_state)
        return metrics.model_dump()
    except Exception as e:
        logger.error(f"Failed to analyze simulation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze simulation: {str(e)}"
        )


@router.get("/simulations/{simulation_id}/analytics/export/{format}")
async def export_analytics(
    simulation_id: str,
    format: str = Path(..., pattern="^(json|csv)$"),
):
    """Export metrics in specified format (json or csv)."""
    logger.info(f"Exporting analytics for {simulation_id} as {format}")

    # Get simulation state
    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(
            status_code=404,
            detail=f"Simulation not found: {simulation_id}"
        )

    # Check if simulation is completed
    if sim_state.status.value not in ["completed", "failed"]:
        status = sim_state.status.value
        raise HTTPException(
            status_code=400,
            detail=f"Simulation not completed yet. Status: {status}"
        )

    try:
        # Run analytics
        metrics = await analytics_agent.analyze_simulation(sim_state)

        # Export in requested format
        if format == "json":
            content = await metrics_exporter.to_json(metrics)
            return {
                "content": content,
                "content_type": "application/json",
                "filename": f"{simulation_id}_analytics.json",
            }
        elif format == "csv":
            content = await metrics_exporter.to_csv(metrics)
            return {
                "content": content,
                "content_type": "text/csv",
                "filename": f"{simulation_id}_analytics.csv",
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format: {format}"
            )

    except Exception as e:
        logger.error(f"Failed to export analytics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export analytics: {str(e)}"
        )


@router.post("/simulations/monte-carlo")
async def run_monte_carlo(config: MonteCarloConfig):
    """Start a Monte Carlo simulation run."""
    logger.info(
        f"Starting Monte Carlo run with {config.iterations} iterations"
    )

    try:
        result = await monte_carlo_runner.run(config)
        return result.model_dump()
    except Exception as e:
        logger.error(f"Monte Carlo run failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Monte Carlo run failed: {str(e)}"
        )


@router.post("/simulations/batch")
async def run_batch(config: BatchConfig):
    """Start a batch execution of multiple scenarios."""
    logger.info(f"Starting batch run with {len(config.scenarios)} scenarios")

    try:
        result = await batch_runner.run_batch(config)
        return result.model_dump()
    except Exception as e:
        logger.error(f"Batch run failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Batch run failed: {str(e)}"
        )


@router.post("/cost-estimate", response_model=CostEstimate)
async def get_cost_estimate(request: CostEstimateRequest):
    """Get pre-simulation cost estimate."""
    logger.info("Calculating cost estimate")

    try:
        estimate = cost_estimator.estimate(
            agent_count=request.agent_count,
            rounds=request.rounds,
            monte_carlo_iterations=request.monte_carlo_iterations,
            provider=request.provider,
        )
        return estimate
    except Exception as e:
        logger.error(f"Cost estimation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Cost estimation failed: {str(e)}"
        )


@router.post("/cost-estimate/batch", response_model=CostEstimate)
async def get_batch_cost_estimate(request: BatchCostEstimateRequest):
    """Get cost estimate for batch execution."""
    logger.info("Calculating batch cost estimate")

    try:
        estimate = cost_estimator.estimate_batch_cost(
            scenario_count=request.scenario_count,
            agent_count=request.agent_count,
            rounds=request.rounds,
            monte_carlo_iterations=request.monte_carlo_iterations,
            provider=request.provider,
        )
        return estimate
    except Exception as e:
        logger.error(f"Batch cost estimation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Batch cost estimation failed: {str(e)}"
        )


# Shapley Attribution Endpoints
@router.post(
    "/simulations/{simulation_id}/attribution",
    response_model=AttributionResult,
)
async def compute_attribution(
    simulation_id: str,
    request: AttributionRequest | None = None,
):
    """Compute Shapley value-based outcome attribution."""
    logger.info(f"Computing attribution for simulation: {simulation_id}")

    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(
            status_code=404,
            detail=f"Simulation not found: {simulation_id}"
        )

    if sim_state.status.value not in ["completed", "failed"]:
        raise HTTPException(
            status_code=400,
            detail="Simulation must be completed for attribution analysis"
        )

    try:
        llm = get_llm_provider()
        analyzer = ShapleyAnalyzer(llm_provider=llm)

        outcome_metric = (
            request.outcome_metric if request else "overall_outcome"
        )
        result = await analyzer.compute_attribution(
            sim_state, outcome_metric
        )
        return result
    except Exception as e:
        logger.error(f"Attribution computation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Attribution computation failed: {str(e)}"
        )


# Fairness Audit Endpoints
@router.post(
    "/simulations/{simulation_id}/fairness-audit",
    response_model=FairnessReport,
)
async def audit_fairness(
    simulation_id: str,
    request: FairnessAuditRequest | None = None,
):
    """Audit simulation for bias and fairness issues."""
    logger.info(f"Auditing fairness for simulation: {simulation_id}")

    sim_state = await simulation_engine.get_simulation(simulation_id)
    if not sim_state:
        raise HTTPException(
            status_code=404,
            detail=f"Simulation not found: {simulation_id}"
        )

    if sim_state.status.value not in ["completed", "failed"]:
        raise HTTPException(
            status_code=400,
            detail="Simulation must be completed for fairness audit"
        )

    try:
        llm = get_llm_provider()
        auditor = FairnessAuditor(llm_provider=llm)

        perturbation_type = (
            request.perturbation_type if request else "gender"
        )
        result = await auditor.audit_simulation(
            sim_state, perturbation_type
        )
        return result
    except Exception as e:
        logger.error(f"Fairness audit failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Fairness audit failed: {str(e)}"
        )


# Cross-Simulation Learning Endpoints
class CrossSimulationOptInRequest(BaseModel):
    simulation_id: str


@router.post("/cross-simulation/opt-in")
async def cross_simulation_opt_in(request: CrossSimulationOptInRequest):
    logger.info(f"Opting in simulation {request.simulation_id}")
    try:
        result = cross_simulation_learner.opt_in(request.simulation_id)
        return {"simulation_id": request.simulation_id, "opted_in": result}
    except Exception as e:
        logger.error(f"Cross-simulation opt-in failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Cross-simulation opt-in failed: {str(e)}"
        )


@router.get("/cross-simulation/patterns")
async def get_cross_simulation_patterns(min_simulations: int = 10):
    logger.info("Getting cross-simulation aggregate patterns")
    try:
        patterns = cross_simulation_learner.get_aggregate_patterns(
            min_simulations
        )
        return patterns
    except Exception as e:
        logger.error(f"Failed to get patterns: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get patterns: {str(e)}"
        )


@router.get("/cross-simulation/privacy-report/{simulation_id}")
async def get_cross_simulation_privacy_report(simulation_id: str):
    logger.info(f"Getting privacy report for simulation {simulation_id}")
    try:
        report = cross_simulation_learner.get_privacy_report(simulation_id)
        return report
    except Exception as e:
        logger.error(f"Failed to get privacy report: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get privacy report: {str(e)}"
        )


@router.post("/cross-simulation/improve-archetypes")
async def get_archetype_improvements():
    logger.info("Getting archetype improvement suggestions")
    try:
        patterns = cross_simulation_learner.get_aggregate_patterns()
        suggestions = cross_simulation_learner.improve_archetypes(patterns)
        return {"suggestions": suggestions, "patterns_used": patterns}
    except Exception as e:
        logger.error(f"Failed to get archetype improvements: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get archetype improvements: {str(e)}"
        )
