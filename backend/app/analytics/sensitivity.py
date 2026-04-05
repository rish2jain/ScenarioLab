"""Sensitivity analysis for simulation parameters."""

import logging

from pydantic import BaseModel

from app.simulation.models import AgentState, SimulationState

logger = logging.getLogger(__name__)


class SensitivityParameter(BaseModel):
    """A parameter analyzed for sensitivity."""

    name: str
    description: str
    base_value: float
    low_value: float
    high_value: float
    low_outcome: float
    high_outcome: float
    impact_score: float  # Magnitude of impact


class TornadoChartData(BaseModel):
    """Data for rendering a tornado chart."""

    simulation_id: str
    parameters: list[SensitivityParameter]
    baseline_outcome: dict  # {metric: value}
    outcome_metrics: list[str]  # Available metrics to analyze


class SensitivityAnalyzer:
    """Analyze sensitivity of simulation outcomes to parameter changes."""

    # Parameters to analyze for sensitivity
    AGENT_PARAMETERS = [
        ("risk_tolerance", "Agent Risk Tolerance", 0.5, 0.2, 0.8),
        ("authority_level", "Agent Authority Level", 0.6, 0.3, 0.9),
        ("coalition_tendency", "Coalition Formation Tendency", 0.4, 0.1, 0.7),
    ]

    ENVIRONMENT_PARAMETERS = [
        ("time_pressure", "Time Pressure", 0.5, 0.2, 0.8),
        ("information_asymmetry", "Information Asymmetry", 0.3, 0.1, 0.6),
        ("decision_threshold", "Decision Threshold", 0.6, 0.4, 0.8),
    ]

    def __init__(self, llm_provider=None):
        self.llm = llm_provider

    async def analyze(
        self,
        simulation_state: SimulationState,
        outcome_metrics: list[str] | None = None,
    ) -> TornadoChartData:
        """Run sensitivity analysis on a completed simulation.

        Args:
            simulation_state: The completed simulation to analyze
            outcome_metrics: List of metrics to analyze (default: all)

        Returns:
            TornadoChartData with ranked parameters by impact
        """
        logger.info(f"Running sensitivity analysis for {simulation_state.config.id}")

        if outcome_metrics is None:
            outcome_metrics = [
                "policy_adoption_rate",
                "time_to_consensus",
                "compliance_violation_rate",
            ]

        # Extract baseline outcomes from simulation results
        baseline = self._extract_baseline_outcomes(simulation_state)

        # Analyze each parameter
        parameters: list[SensitivityParameter] = []

        # Agent-level parameters
        for agent in simulation_state.agents:
            agent_params = await self._analyze_agent_parameters(
                agent, simulation_state, baseline
            )
            parameters.extend(agent_params)

        # Environment-level parameters
        env_params = await self._analyze_environment_parameters(
            simulation_state, baseline
        )
        parameters.extend(env_params)

        # Rank by impact score (descending)
        parameters.sort(key=lambda p: abs(p.impact_score), reverse=True)

        return TornadoChartData(
            simulation_id=simulation_state.config.id,
            parameters=parameters[:12],  # Top 12 parameters
            baseline_outcome=baseline,
            outcome_metrics=outcome_metrics,
        )

    def _extract_baseline_outcomes(
        self, simulation_state: SimulationState
    ) -> dict:
        """Extract baseline outcome metrics from simulation results."""
        # Calculate metrics from simulation data
        total_messages = sum(
            len(r.messages) for r in simulation_state.rounds
        )

        # Time to consensus: rounds until first decision
        time_to_consensus = None
        for i, round_state in enumerate(simulation_state.rounds):
            if round_state.decisions:
                time_to_consensus = i + 1
                break

        # Policy adoption rate: estimate from decisions
        approved_decisions = sum(
            1 for r in simulation_state.rounds
            for d in r.decisions
            if d.get("evaluation", {}).get("outcome")
            in ["approved", "accepted", "proposal_accepted"]
        )
        total_decisions = sum(
            len(r.decisions) for r in simulation_state.rounds
        )
        policy_adoption_rate = (
            (approved_decisions / total_decisions * 100)
            if total_decisions > 0 else 0
        )

        # Compliance violation rate: estimate from agent behavior
        # (simplified - in production would use AnalyticsAgent)
        compliance_violation_rate = 5.0  # Default baseline

        return {
            "policy_adoption_rate": policy_adoption_rate,
            "time_to_consensus": (
                time_to_consensus or
                simulation_state.config.total_rounds
            ),
            "compliance_violation_rate": compliance_violation_rate,
            "total_messages": total_messages,
            "total_rounds": simulation_state.current_round,
        }

    async def _analyze_agent_parameters(
        self,
        agent: AgentState,
        simulation_state: SimulationState,
        baseline: dict,
    ) -> list[SensitivityParameter]:
        """Analyze sensitivity of agent-specific parameters."""
        parameters = []

        # Get agent customization from config
        agent_config = None
        for ac in simulation_state.config.agents:
            if ac.id == agent.id:
                agent_config = ac
                break

        custom_params = agent_config.customization if agent_config else {}

        # Risk tolerance
        risk_base = custom_params.get("risk_tolerance", 0.5)
        param = SensitivityParameter(
            name=f"{agent.name} Risk Tolerance",
            description=f"Risk appetite for {agent.name} "
                        f"({agent.archetype_id})",
            base_value=risk_base,
            low_value=max(0.1, risk_base - 0.3),
            high_value=min(1.0, risk_base + 0.3),
            low_outcome=baseline.get("policy_adoption_rate", 50) * 0.85,
            high_outcome=baseline.get("policy_adoption_rate", 50) * 1.15,
            impact_score=self._estimate_impact(
                risk_base, "risk_tolerance", agent
            ),
        )
        parameters.append(param)

        # Authority level
        authority_base = custom_params.get("authority_level", 0.6)
        param = SensitivityParameter(
            name=f"{agent.name} Authority Level",
            description=f"Decision authority for {agent.name}",
            base_value=authority_base,
            low_value=max(0.1, authority_base - 0.3),
            high_value=min(1.0, authority_base + 0.3),
            low_outcome=baseline.get("time_to_consensus", 10) * 1.2,
            high_outcome=baseline.get("time_to_consensus", 10) * 0.8,
            impact_score=self._estimate_impact(
                authority_base, "authority", agent
            ),
        )
        parameters.append(param)

        # Coalition tendency
        coalition_base = custom_params.get("coalition_tendency", 0.4)
        coalition_count = (
            len(agent.coalition_members)
            if agent.coalition_members else 0
        )
        param = SensitivityParameter(
            name=f"{agent.name} Coalition Tendency",
            description=f"Likelihood to form alliances for {agent.name}",
            base_value=coalition_base,
            low_value=max(0.0, coalition_base - 0.3),
            high_value=min(1.0, coalition_base + 0.3),
            low_outcome=coalition_count,
            high_outcome=coalition_count + 2,
            impact_score=self._estimate_impact(
                coalition_base, "coalition", agent
            ),
        )
        parameters.append(param)

        return parameters

    async def _analyze_environment_parameters(
        self,
        simulation_state: SimulationState,
        baseline: dict,
    ) -> list[SensitivityParameter]:
        """Analyze sensitivity of environment-level parameters."""
        parameters = []

        config_params = simulation_state.config.parameters or {}

        # Time pressure
        time_pressure = config_params.get("time_pressure", 0.5)
        param = SensitivityParameter(
            name="Environment Time Pressure",
            description="Urgency level in the decision environment",
            base_value=time_pressure,
            low_value=max(0.1, time_pressure - 0.3),
            high_value=min(1.0, time_pressure + 0.3),
            low_outcome=baseline.get("time_to_consensus", 10) * 1.3,
            high_outcome=baseline.get("time_to_consensus", 10) * 0.7,
            impact_score=abs(time_pressure - 0.5) * 10 + 5,
        )
        parameters.append(param)

        # Information asymmetry
        info_asymmetry = config_params.get("information_asymmetry", 0.3)
        param = SensitivityParameter(
            name="Information Asymmetry",
            description="Distribution of information across agents",
            base_value=info_asymmetry,
            low_value=max(0.0, info_asymmetry - 0.2),
            high_value=min(1.0, info_asymmetry + 0.3),
            low_outcome=baseline.get("compliance_violation_rate", 5) * 0.6,
            high_outcome=baseline.get("compliance_violation_rate", 5) * 1.8,
            impact_score=abs(info_asymmetry - 0.3) * 15 + 3,
        )
        parameters.append(param)

        # Decision threshold
        decision_threshold = config_params.get("decision_threshold", 0.6)
        param = SensitivityParameter(
            name="Decision Threshold",
            description="Support required to pass a decision",
            base_value=decision_threshold,
            low_value=max(0.4, decision_threshold - 0.2),
            high_value=min(0.9, decision_threshold + 0.2),
            low_outcome=baseline.get("policy_adoption_rate", 50) * 1.25,
            high_outcome=baseline.get("policy_adoption_rate", 50) * 0.75,
            impact_score=abs(decision_threshold - 0.5) * 12 + 4,
        )
        parameters.append(param)

        return parameters

    def _estimate_impact(
        self,
        value: float,
        param_type: str,
        agent: AgentState,
    ) -> float:
        """Estimate the impact score for a parameter.

        Higher values indicate greater sensitivity.
        """
        # Base impact varies by parameter type
        base_impacts = {
            "risk_tolerance": 8.0,
            "authority": 10.0,
            "coalition": 6.0,
            "time_pressure": 12.0,
            "information_asymmetry": 7.0,
            "decision_threshold": 9.0,
        }

        base = base_impacts.get(param_type, 5.0)

        # Modify based on value extremity (far from 0.5 = more impact)
        extremity_factor = abs(value - 0.5) * 2

        # Modify based on agent archetype
        archetype_multipliers = {
            "aggressor": 1.2,
            "defender": 1.0,
            "mediator": 0.8,
            "analyst": 1.1,
            "influencer": 1.15,
            "skeptic": 0.9,
        }
        archetype_mult = archetype_multipliers.get(agent.archetype_id, 1.0)

        return round(base * (1 + extremity_factor * 0.3) * archetype_mult, 2)
