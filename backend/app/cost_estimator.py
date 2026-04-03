"""Pre-simulation cost estimation."""

import logging

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CostEstimate(BaseModel):
    """Cost estimate for a simulation run."""
    total_estimated_tokens: int
    total_estimated_cost_usd: float
    breakdown: dict  # {agent_reasoning: X, report_generation: Y, analytics: Z}
    cost_per_provider: dict  # {openai: X, anthropic: Y, ollama: 0}
    optimization_suggestions: list[str]


class CostEstimator:
    """Estimate LLM token usage and cost before simulation."""

    # Token cost per 1K tokens (approximate)
    PROVIDER_COSTS = {
        "openai": {"input": 0.03, "output": 0.06},  # GPT-4 class
        "anthropic": {"input": 0.025, "output": 0.075},
        "google": {"input": 0.00125, "output": 0.005},
        "qwen": {"input": 0.008, "output": 0.024},
        "ollama": {"input": 0.0, "output": 0.0},
        "llamacpp": {"input": 0.0, "output": 0.0},
    }

    # Estimated tokens per operation
    TOKENS_PER_AGENT_MESSAGE = 700  # ~500 input + ~200 output
    TOKENS_PER_REPORT_GENERATION = 2000
    TOKENS_PER_ANALYTICS_ANALYSIS = 1500

    def estimate(
        self,
        agent_count: int,
        rounds: int,
        monte_carlo_iterations: int = 1,
        provider: str = "openai"
    ) -> CostEstimate:
        """Calculate estimated cost."""
        logger.info(
            f"Estimating cost: {agent_count} agents, {rounds} rounds, "
            f"{monte_carlo_iterations} MC iterations, provider: {provider}"
        )

        # Calculate base tokens for agent interactions
        # Each agent speaks ~2 times per round
        messages_per_round = agent_count * 2
        total_messages = messages_per_round * rounds * monte_carlo_iterations
        agent_tokens = total_messages * self.TOKENS_PER_AGENT_MESSAGE

        # Report generation tokens
        report_tokens = (
            self.TOKENS_PER_REPORT_GENERATION * monte_carlo_iterations
        )

        # Analytics tokens (only run once per simulation, not per MC iteration)
        analytics_tokens = self.TOKENS_PER_ANALYTICS_ANALYSIS

        total_tokens = agent_tokens + report_tokens + analytics_tokens

        # Calculate cost
        provider_costs = self.PROVIDER_COSTS.get(
            provider, self.PROVIDER_COSTS["openai"]
        )

        # Assume 70% input, 30% output split
        input_tokens = int(total_tokens * 0.7)
        output_tokens = int(total_tokens * 0.3)

        input_cost = (input_tokens / 1000) * provider_costs["input"]
        output_cost = (output_tokens / 1000) * provider_costs["output"]
        total_cost = input_cost + output_cost

        # Build cost breakdown
        breakdown = {
            "agent_reasoning": {
                "tokens": agent_tokens,
                "cost_usd": round(
                    (agent_tokens / 1000) * (
                        provider_costs["input"] * 0.7 +
                        provider_costs["output"] * 0.3
                    ),
                    4
                ),
                "description": "Agent message generation and reasoning",
            },
            "report_generation": {
                "tokens": report_tokens,
                "cost_usd": round(
                    (report_tokens / 1000) * (
                        provider_costs["input"] * 0.7 +
                        provider_costs["output"] * 0.3
                    ),
                    4
                ),
                "description": "Final report generation",
            },
            "analytics": {
                "tokens": analytics_tokens,
                "cost_usd": round(
                    (analytics_tokens / 1000) * (
                        provider_costs["input"] * 0.7 +
                        provider_costs["output"] * 0.3
                    ),
                    4
                ),
                "description": "Post-simulation analytics analysis",
            },
        }

        # Cost per provider comparison
        cost_per_provider = {}
        for prov, costs in self.PROVIDER_COSTS.items():
            prov_input_cost = (input_tokens / 1000) * costs["input"]
            prov_output_cost = (output_tokens / 1000) * costs["output"]
            total_prov_cost = prov_input_cost + prov_output_cost
            cost_per_provider[prov] = round(total_prov_cost, 4)

        # Generate optimization suggestions
        suggestions = self._generate_suggestions(
            agent_count, rounds, monte_carlo_iterations, total_cost, provider
        )

        estimate = CostEstimate(
            total_estimated_tokens=total_tokens,
            total_estimated_cost_usd=round(total_cost, 4),
            breakdown=breakdown,
            cost_per_provider=cost_per_provider,
            optimization_suggestions=suggestions,
        )

        logger.info(
            f"Cost estimate complete: ${estimate.total_estimated_cost_usd} "
            f"({estimate.total_estimated_tokens} tokens)"
        )
        return estimate

    def _generate_suggestions(
        self,
        agent_count: int,
        rounds: int,
        monte_carlo_iterations: int,
        total_cost: float,
        provider: str
    ) -> list[str]:
        """Generate cost optimization suggestions."""
        suggestions = []

        # Suggest reducing agents
        if agent_count > 8:
            suggestions.append(
                f"Consider reducing agent count from {agent_count} to 6-8 "
                "to significantly reduce costs without losing key perspectives"
            )

        # Suggest reducing rounds
        if rounds > 15:
            suggestions.append(
                f"Consider reducing rounds from {rounds} to 10-12 "
                "if the scenario allows for faster consensus"
            )

        # Suggest Monte Carlo optimization
        if monte_carlo_iterations > 30:
            suggestions.append(
                f"Consider reducing Monte Carlo iterations from "
                f"{monte_carlo_iterations} to 20-30; statistical "
                "confidence typically plateaus after 20-25 runs"
            )

        # Suggest local LLM for testing
        if provider in ["openai", "anthropic"] and total_cost > 5.0:
            suggestions.append(
                "Consider using Ollama or llama.cpp for testing "
                "and development (zero API cost)"
            )

        # Suggest cheaper provider
        if provider == "openai" and total_cost > 1.0:
            suggestions.append(
                "Consider using Google Gemini or Qwen for "
                "lower-cost alternatives with good performance"
            )

        # Warn about high cost
        if total_cost > 10.0:
            suggestions.append(
                f"WARNING: Estimated cost (${total_cost:.2f}) is high. "
                "Consider running a smaller test first."
            )

        if not suggestions:
            suggestions.append(
                "Configuration looks cost-effective for the expected output"
            )

        return suggestions

    def estimate_batch_cost(
        self,
        scenario_count: int,
        agent_count: int,
        rounds: int,
        monte_carlo_iterations: int = 0,
        provider: str = "openai"
    ) -> CostEstimate:
        """Estimate cost for batch execution."""
        # Base estimate for single run
        base_estimate = self.estimate(
            agent_count, rounds, monte_carlo_iterations, provider
        )

        # Multiply by scenario count
        total_tokens = base_estimate.total_estimated_tokens * scenario_count
        total_cost = base_estimate.total_estimated_cost_usd * scenario_count

        # Adjust breakdown
        breakdown = {}
        for key, value in base_estimate.breakdown.items():
            breakdown[key] = {
                "tokens": value["tokens"] * scenario_count,
                "cost_usd": round(value["cost_usd"] * scenario_count, 4),
                "description": value["description"],
            }

        # Cost per provider
        cost_per_provider = {
            prov: round(cost * scenario_count, 4)
            for prov, cost in base_estimate.cost_per_provider.items()
        }

        # Generate batch-specific suggestions
        suggestions = base_estimate.optimization_suggestions.copy()
        suggestions.insert(0, f"Batch execution: {scenario_count} scenarios")

        if total_cost > 50.0:
            suggestions.append(
                f"WARNING: Batch cost (${total_cost:.2f}) is significant. "
                "Consider running a subset of scenarios first."
            )

        return CostEstimate(
            total_estimated_tokens=total_tokens,
            total_estimated_cost_usd=round(total_cost, 4),
            breakdown=breakdown,
            cost_per_provider=cost_per_provider,
            optimization_suggestions=suggestions,
        )
