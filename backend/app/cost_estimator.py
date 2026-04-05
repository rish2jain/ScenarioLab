"""Pre-simulation cost estimation."""

import logging

from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)


class CostEstimate(BaseModel):
    """Cost estimate for a simulation run.

    For batch estimates, ``total_estimated_tokens`` and monetary fields scale with
    ``scenario_count`` (total work across scenarios). Duration fields are
    wall-clock hints: they scale with
    ``scenario_count / parallelism_factor``. With ``parallelism_factor == 1``,
    durations are the **serial / worst-case** wall time; larger factors model
    overlapping execution (e.g. ``parallelism_factor == scenario_count`` implies
    all scenarios run in parallel).
    """

    total_estimated_tokens: int
    total_estimated_cost_usd: float
    breakdown: dict  # {agent_reasoning: X, report_generation: Y, analytics: Z}
    cost_per_provider: dict  # {openai: X, anthropic: Y, ollama: 0}
    optimization_suggestions: list[str]
    # Effective parallelism used only for batch duration math (single-run = 1).
    parallelism_factor: float = Field(
        default=1.0,
        gt=0,
        description="Batch only: duration scales as scenario_count / parallelism_factor.",
    )
    # Wall-clock hints (LLM latency varies by provider/load)
    estimated_duration_minutes: float = 0.0
    estimated_duration_min_minutes: float = 0.0
    estimated_duration_max_minutes: float = 0.0
    duration_breakdown: dict = Field(default_factory=dict)


class CostEstimator:
    """Estimate LLM token usage and cost before simulation."""

    # Token cost per 1K tokens (approximate, current-gen models mid-2025).
    # Default per-provider prices assume mid-tier model for each family.
    PROVIDER_COSTS = {
        "openai": {"input": 0.0025, "output": 0.01},
        "anthropic": {"input": 0.003, "output": 0.015},
        "google": {"input": 0.00125, "output": 0.005},
        "qwen": {"input": 0.002, "output": 0.006},
        "ollama": {"input": 0.0, "output": 0.0},
        "llamacpp": {"input": 0.0, "output": 0.0},
    }

    # Model-specific overrides (substring match against LLM_MODEL_NAME).
    # When a model name matches, these costs replace the provider default.
    MODEL_COSTS: dict[str, dict[str, float]] = {
        # OpenAI
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4o": {"input": 0.0025, "output": 0.01},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4.1-mini": {"input": 0.0004, "output": 0.0016},
        "gpt-4.1": {"input": 0.002, "output": 0.008},
        "o3-mini": {"input": 0.0011, "output": 0.0044},
        # Anthropic
        "claude-3-5-haiku": {"input": 0.0008, "output": 0.004},
        "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
        "claude-sonnet-4": {"input": 0.003, "output": 0.015},
        "claude-opus-4": {"input": 0.015, "output": 0.075},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        # Google
        "gemini-2.0-flash": {"input": 0.0001, "output": 0.0004},
        "gemini-2.5-pro": {"input": 0.00125, "output": 0.01},
        "gemini-2.5-flash": {"input": 0.00015, "output": 0.0006},
        # Qwen
        "qwen-plus": {"input": 0.002, "output": 0.006},
        "qwen-turbo": {"input": 0.0005, "output": 0.002},
    }

    @classmethod
    def _resolve_costs(cls, provider: str, model_name: str | None = None) -> dict[str, float]:
        """Resolve pricing: model-specific override if available, else provider default."""
        if model_name:
            model_lower = model_name.lower()
            # Try exact match first, then substring match (longest wins).
            for key in sorted(cls.MODEL_COSTS, key=len, reverse=True):
                if key in model_lower:
                    return cls.MODEL_COSTS[key]
        return cls.PROVIDER_COSTS.get(provider, cls.PROVIDER_COSTS["openai"])

    # Estimated tokens per operation
    TOKENS_PER_AGENT_MESSAGE = 800  # ~600 input (context+prompt) + ~200 output
    TOKENS_PER_REPORT_GENERATION = 2500  # 5 parallel sections, shared context
    TOKENS_PER_ANALYTICS_ANALYSIS = 1200  # batched sentiment + keyword metrics

    # Per-operation input/output ratio — more accurate than a single global split.
    # Agent messages carry large system prompts (high input ratio).
    # Report generation sends full context per section (very high input).
    # Analytics is mostly batched prompts with short JSON replies.
    _IO_RATIO = {
        "agent": (0.75, 0.25),
        "report": (0.85, 0.15),
        "analytics": (0.80, 0.20),
    }

    # Duration: seconds per agent LLM call (min / avg / max band).
    # Cloud API providers (openai, anthropic, google) — faster.
    # CLI-based providers (cli-codex, cli-claude, cli-chatgpt, cli-gemini,
    # ollama, llamacpp) shell out per call and are much slower.
    SECS_PER_LLM_CALL = {
        "cloud": {"min": 4.0, "mid": 8.0, "max": 18.0},
        "cli": {"min": 15.0, "mid": 30.0, "max": 60.0},
    }
    SECS_REPORT = {"cloud": 55.0, "cli": 300.0}
    SECS_ANALYTICS = {"cloud": 40.0, "cli": 180.0}

    _CLI_PROVIDERS = {"ollama", "llamacpp", "cli-codex", "cli-claude", "cli-chatgpt", "cli-gemini"}

    @classmethod
    def _provider_tier(cls, provider: str) -> str:
        """Wall-clock tier for duration estimates: ``"cli"`` or ``"cloud"``.

        **Precedence:** ``getattr(settings, "llm_provider", None)`` (stripped and
        lowercased) is resolved *before* the ``provider`` argument. If that value is
        in :attr:`_CLI_PROVIDERS` or starts with ``"cli-"``, this returns ``"cli"``
        even when ``provider`` names a different execution path (e.g. a billing
        family such as ``openai``).

        **Fallback:** If settings did not imply CLI, the same ``"cli"`` vs
        ``"cloud"`` decision uses the ``provider`` parameter together with
        :attr:`_CLI_PROVIDERS` (membership only on this path; the ``"cli-"`` prefix
        rule applies to settings first).

        :func:`cost_estimator_provider_key` maps CLI providers to a **billing** family
        (e.g. ``cli-chatgpt`` → ``openai``). Token/cost math uses that family; duration
        must still use the **CLI** band when the server is actually shelling out.
        """
        raw = (getattr(settings, "llm_provider", None) or "").strip().lower()
        if raw in cls._CLI_PROVIDERS or raw.startswith("cli-"):
            return "cli"
        if provider in cls._CLI_PROVIDERS:
            return "cli"
        return "cloud"

    @staticmethod
    def _mc_multiplier_for_cost(monte_carlo_iterations: int) -> int:
        """Monte Carlo factor for token math.

        Batch execution uses ``0`` to mean one run per scenario (no MC sweep); the
        cost model must not multiply agent/report work by zero. ``1`` is the
        minimum meaningful multiplier (single pass).
        """
        return monte_carlo_iterations if monte_carlo_iterations > 0 else 1

    def estimate(
        self,
        agent_count: int,
        rounds: int,
        monte_carlo_iterations: int = 1,
        provider: str = "openai",
        *,
        model_name: str | None = None,
        include_report: bool = True,
        include_analytics: bool = True,
        extended_seed_context: bool = False,
    ) -> CostEstimate:
        """Calculate estimated cost and rough duration.

        Optional features (keyword-only) match the simulation wizard toggles:
        - model_name: override model for model-specific pricing (falls back to
          ``settings.llm_model_name`` then provider default).
        - include_report / include_analytics: omit post-run token buckets when False.
        - extended_seed_context: bump agent token estimate for long seed context.
        """
        logger.info(
            f"Estimating cost: {agent_count} agents, {rounds} rounds, "
            f"{monte_carlo_iterations} MC iterations, provider: {provider}"
        )

        # Calculate base tokens for agent interactions
        # Each agent speaks ~2 times per round
        mc = self._mc_multiplier_for_cost(monte_carlo_iterations)
        messages_per_round = agent_count * 2
        total_messages = messages_per_round * rounds * mc
        agent_tokens = total_messages * self.TOKENS_PER_AGENT_MESSAGE
        if extended_seed_context:
            agent_tokens = int(agent_tokens * 1.15)

        # Report generation tokens
        report_tokens = (self.TOKENS_PER_REPORT_GENERATION * mc) if include_report else 0

        # Analytics tokens (only run once per simulation, not per MC iteration)
        analytics_tokens = self.TOKENS_PER_ANALYTICS_ANALYSIS if include_analytics else 0

        total_tokens = agent_tokens + report_tokens + analytics_tokens

        # Calculate cost using per-operation I/O ratios.
        # Resolve model-specific pricing when a model name is available.
        resolved_model = model_name or getattr(settings, "llm_model_name", None)
        provider_costs = self._resolve_costs(provider, resolved_model)

        def _bucket_cost(tokens: int, io_key: str) -> float:
            in_r, out_r = self._IO_RATIO[io_key]
            return (tokens / 1000) * (provider_costs["input"] * in_r + provider_costs["output"] * out_r)

        agent_cost = _bucket_cost(agent_tokens, "agent")
        report_cost = _bucket_cost(report_tokens, "report")
        analytics_cost = _bucket_cost(analytics_tokens, "analytics")
        total_cost = agent_cost + report_cost + analytics_cost

        # Weighted-average I/O split for the cross-provider comparison table
        if total_tokens > 0:
            input_tokens = int(
                agent_tokens * self._IO_RATIO["agent"][0]
                + report_tokens * self._IO_RATIO["report"][0]
                + analytics_tokens * self._IO_RATIO["analytics"][0]
            )
            output_tokens = total_tokens - input_tokens
        else:
            input_tokens = 0
            output_tokens = 0

        # Build cost breakdown
        breakdown = {
            "agent_reasoning": {
                "tokens": agent_tokens,
                "cost_usd": round(agent_cost, 4),
                "description": "Agent message generation and reasoning",
            },
            "report_generation": {
                "tokens": report_tokens,
                "cost_usd": round(report_cost, 4),
                "description": "Final report generation",
            },
            "analytics": {
                "tokens": analytics_tokens,
                "cost_usd": round(analytics_cost, 4),
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
        suggestions = self._generate_suggestions(agent_count, rounds, monte_carlo_iterations, total_cost, provider)

        dur_mid, dur_min, dur_max, dur_breakdown = self._estimate_duration(
            total_messages=total_messages,
            include_report=include_report,
            include_analytics=include_analytics,
            provider=provider,
        )

        estimate = CostEstimate(
            total_estimated_tokens=total_tokens,
            total_estimated_cost_usd=round(total_cost, 4),
            breakdown=breakdown,
            cost_per_provider=cost_per_provider,
            optimization_suggestions=suggestions,
            estimated_duration_minutes=round(dur_mid, 2),
            estimated_duration_min_minutes=round(dur_min, 2),
            estimated_duration_max_minutes=round(dur_max, 2),
            duration_breakdown=dur_breakdown,
        )

        logger.info(
            f"Cost estimate complete: ${estimate.total_estimated_cost_usd} "
            f"({estimate.total_estimated_tokens} tokens)"
        )
        return estimate

    def _estimate_duration(
        self,
        *,
        total_messages: int,
        include_report: bool,
        include_analytics: bool,
        provider: str = "openai",
    ) -> tuple[float, float, float, dict]:
        """Return (mid, min, max) minutes and a small breakdown dict."""
        tier = self._provider_tier(provider)
        call_secs = self.SECS_PER_LLM_CALL[tier]
        core_sec_min = total_messages * call_secs["min"]
        core_sec_mid = total_messages * call_secs["mid"]
        core_sec_max = total_messages * call_secs["max"]
        report_secs = self.SECS_REPORT[tier]
        analytics_secs = self.SECS_ANALYTICS[tier]
        extra = 0.0
        if include_report:
            extra += report_secs
        if include_analytics:
            extra += analytics_secs
        mid = (core_sec_mid + extra) / 60.0
        lo = (core_sec_min + extra) / 60.0
        hi = (core_sec_max + extra) / 60.0
        breakdown = {
            "agent_llm_calls_mid_minutes": round(core_sec_mid / 60.0, 2),
            "post_run_report_minutes": round(report_secs / 60.0, 2) if include_report else 0.0,
            "post_run_analytics_minutes": (round(analytics_secs / 60.0, 2) if include_analytics else 0.0),
        }
        return mid, lo, hi, breakdown

    def _generate_suggestions(
        self,
        agent_count: int,
        rounds: int,
        monte_carlo_iterations: int,
        total_cost: float,
        provider: str,
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
                f"Consider reducing rounds from {rounds} to 10-12 " "if the scenario allows for faster consensus"
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
            suggestions.append("Consider using Ollama or llama.cpp for testing " "and development (zero API cost)")

        # Suggest cheaper provider
        if provider == "openai" and total_cost > 1.0:
            suggestions.append(
                "Consider using Google Gemini or Qwen for " "lower-cost alternatives with good performance"
            )

        # Warn about high cost
        if total_cost > 10.0:
            suggestions.append(
                f"WARNING: Estimated cost (${total_cost:.2f}) is high. " "Consider running a smaller test first."
            )

        if not suggestions:
            suggestions.append("Configuration looks cost-effective for the expected output")

        return suggestions

    def estimate_batch_cost(
        self,
        scenario_count: int,
        agent_count: int,
        rounds: int,
        monte_carlo_iterations: int = 0,
        provider: str = "openai",
        *,
        model_name: str | None = None,
        parallelism_factor: float = 1.0,
    ) -> CostEstimate:
        """Estimate cost for batch execution.

        Token and dollar totals scale with ``scenario_count`` (total work).
        Duration fields scale with ``scenario_count / parallelism_factor``:
        ``parallelism_factor=1`` is serial wall-clock; higher values model
        concurrent runs.
        """
        # Defense-in-depth: API paths validate via BatchCostEstimateRequest and the
        # returned CostEstimate (both use Field(gt=0) on parallelism_factor), but
        # estimate_batch_cost can be called directly with arbitrary floats.
        if parallelism_factor <= 0:
            raise ValueError("parallelism_factor must be > 0")

        # Base estimate for single run
        base_estimate = self.estimate(
            agent_count,
            rounds,
            monte_carlo_iterations,
            provider,
            model_name=model_name,
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
            prov: round(cost * scenario_count, 4) for prov, cost in base_estimate.cost_per_provider.items()
        }

        # Generate batch-specific suggestions
        suggestions = base_estimate.optimization_suggestions.copy()
        suggestions.insert(0, f"Batch execution: {scenario_count} scenarios")

        if total_cost > 50.0:
            suggestions.append(
                f"WARNING: Batch cost (${total_cost:.2f}) is significant. "
                "Consider running a subset of scenarios first."
            )

        sc = float(scenario_count)
        pf = float(parallelism_factor)
        duration_scale = sc / pf

        return CostEstimate(
            total_estimated_tokens=total_tokens,
            total_estimated_cost_usd=round(total_cost, 4),
            breakdown=breakdown,
            cost_per_provider=cost_per_provider,
            optimization_suggestions=suggestions,
            parallelism_factor=pf,
            estimated_duration_minutes=round(base_estimate.estimated_duration_minutes * duration_scale, 2),
            estimated_duration_min_minutes=round(base_estimate.estimated_duration_min_minutes * duration_scale, 2),
            estimated_duration_max_minutes=round(base_estimate.estimated_duration_max_minutes * duration_scale, 2),
            duration_breakdown={
                k: round(v * duration_scale, 4) if isinstance(v, (int, float)) else v
                for k, v in base_estimate.duration_breakdown.items()
            },
        )
