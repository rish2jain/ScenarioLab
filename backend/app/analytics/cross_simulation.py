"""Cross-Simulation Learning with differential privacy."""

import asyncio
import logging
import math
import random
import threading
from collections import defaultdict
from typing import Any

from app.api_integrations.database import (
    cross_simulation_repo,
    ensure_tables,
)
from app.simulation.models import SimulationState

logger = logging.getLogger(__name__)

# In-memory pattern store (write-through cache)
_pattern_store: dict[str, dict] = {}  # simulation_id -> patterns
_opted_in_simulations: set[str] = set()
# pattern_type -> list of patterns
_aggregate_patterns: dict[str, list] = defaultdict(list)
_initialized = False
# Lazily created so the lock is not bound to an arbitrary event loop at import time
# (tests / teardown can replace the loop; see app.db.connection._get_db_init_lock).
_init_lock: asyncio.Lock | None = None
_init_lock_guard = threading.Lock()


def _get_cross_sim_init_lock() -> asyncio.Lock:
    """Return the module init lock, creating it on first use (thread-safe)."""
    global _init_lock  # noqa: PLW0603
    if _init_lock is None:
        with _init_lock_guard:
            if _init_lock is None:
                _init_lock = asyncio.Lock()
    return _init_lock


async def _ensure_loaded() -> None:
    """Ensure cross-simulation data is loaded from database."""
    global _initialized, _opted_in_simulations  # noqa: PLW0603
    if _initialized:
        return
    async with _get_cross_sim_init_lock():
        if _initialized:
            return
        try:
            await ensure_tables()
            opted_in_ids = await cross_simulation_repo.list_opted_in()
            _opted_in_simulations.update(opted_in_ids)
            _initialized = True
            logger.info(f"Loaded {len(_opted_in_simulations)} opted-in simulations " f"from database")
        except Exception as e:
            logger.warning(f"Failed to load cross-sim data from DB: {e}")


class CrossSimulationLearner:
    """Service for cross-simulation learning with privacy guarantees."""

    def __init__(self):
        self.privacy_epsilon = 1.0  # Differential privacy parameter

    async def opt_in(self, simulation_id: str) -> bool:
        """Opt-in a simulation for cross-simulation learning.

        Args:
            simulation_id: ID of the simulation to opt-in.

        Returns:
            True if opted in successfully.
        """
        await _ensure_loaded()
        _opted_in_simulations.add(simulation_id)
        # Save to database
        asyncio.create_task(self._save_opt_in(simulation_id, True))
        logger.info(f"Simulation {simulation_id} opted in for " f"cross-simulation learning")
        return True

    async def _save_opt_in(self, simulation_id: str, opted_in: bool) -> None:
        """Save opt-in status to database."""
        try:
            await cross_simulation_repo.save_opt_in(simulation_id, opted_in)
        except Exception as e:
            logger.warning(f"Failed to save opt-in status to DB: {e}")

    def extract_patterns(self, simulation_state: SimulationState) -> list[dict]:
        """Extract anonymized behavioral patterns from a simulation.

        Args:
            simulation_state: State of the simulation.

        Returns:
            List of extracted patterns.
        """
        patterns = []

        # Extract archetype decision frequencies
        archetype_decisions: dict[str, dict[str, int]] = defaultdict(lambda: {"support": 0, "oppose": 0, "neutral": 0})

        for agent in simulation_state.agents:
            archetype_id = agent.archetype_id
            stance = agent.current_stance.lower()

            # Classify stance
            if any(word in stance for word in ["support", "agree", "favor", "approve"]):
                archetype_decisions[archetype_id]["support"] += 1
            elif any(word in stance for word in ["oppose", "disagree", "against", "reject"]):
                archetype_decisions[archetype_id]["oppose"] += 1
            else:
                archetype_decisions[archetype_id]["neutral"] += 1

        # Convert to patterns with differential privacy
        for archetype_id, decisions in archetype_decisions.items():
            total = sum(decisions.values())
            if total > 0:
                support_rate = decisions["support"] / total
                # Add Laplacian noise for privacy
                noise = self._laplace_noise(self.privacy_epsilon)
                noisy_rate = max(0.0, min(1.0, support_rate + noise))

                pattern = {
                    "pattern_type": "archetype_decision_frequency",
                    "archetype_id": archetype_id,
                    "support_rate": round(noisy_rate, 3),
                    "sample_size": total,
                    "environment": simulation_state.config.environment_type.value,
                }
                patterns.append(pattern)
                _aggregate_patterns["archetype_decision_frequency"].append(pattern)

        # Extract coalition formation patterns
        coalition_patterns = self._extract_coalition_patterns(simulation_state)
        patterns.extend(coalition_patterns)

        # Extract environment-specific outcomes
        outcome_patterns = self._extract_outcome_patterns(simulation_state)
        patterns.extend(outcome_patterns)

        # Store patterns for this simulation
        _pattern_store[simulation_state.config.id] = {
            "patterns": patterns,
            "extracted_at": self._get_timestamp(),
        }

        # Save to database
        asyncio.get_event_loop().create_task(self._save_patterns(simulation_state.config.id, patterns))

        return patterns

    async def _save_patterns(self, simulation_id: str, patterns: list[dict]) -> None:
        """Save patterns to database."""
        try:
            await cross_simulation_repo.save_patterns(simulation_id, patterns, None)
        except Exception as e:
            logger.warning(f"Failed to save patterns to DB: {e}")

    def _extract_coalition_patterns(self, simulation_state: SimulationState) -> list[dict]:
        """Extract coalition formation patterns."""
        patterns = []

        # Analyze coalition members
        coalition_map: dict[str, list[str]] = defaultdict(list)
        for agent in simulation_state.agents:
            for member_id in agent.coalition_members:
                coalition_map[member_id].append(agent.archetype_id)

        # Find archetype pairs that form coalitions
        archetype_pairs: dict[str, int] = defaultdict(int)
        for coalition_id, members in coalition_map.items():
            if len(members) >= 2:
                for i, a1 in enumerate(members):
                    for a2 in members[i + 1 :]:
                        pair = tuple(sorted([a1, a2]))
                        archetype_pairs[f"{pair[0]}-{pair[1]}"] += 1

        for pair, count in archetype_pairs.items():
            noise = self._laplace_noise(self.privacy_epsilon)
            noisy_count = max(0, count + int(noise))

            pattern = {
                "pattern_type": "coalition_formation",
                "archetype_pair": pair,
                "frequency": noisy_count,
                "environment": simulation_state.config.environment_type.value,
            }
            patterns.append(pattern)
            _aggregate_patterns["coalition_formation"].append(pattern)

        return patterns

    def _extract_outcome_patterns(self, simulation_state: SimulationState) -> list[dict]:
        """Extract environment-specific outcome patterns."""
        patterns = []

        if simulation_state.status.value != "completed":
            return patterns

        # Extract round-based metrics
        total_rounds = simulation_state.current_round
        total_messages = sum(len(r.messages) for r in simulation_state.rounds)

        noise = self._laplace_noise(self.privacy_epsilon)
        noisy_rounds = max(1, total_rounds + int(noise))

        pattern = {
            "pattern_type": "environment_outcome",
            "environment": simulation_state.config.environment_type.value,
            "rounds_to_completion": noisy_rounds,
            "message_count": total_messages,
            "consensus_reached": "consensus" in str(simulation_state.results_summary).lower(),
        }
        patterns.append(pattern)
        _aggregate_patterns["environment_outcome"].append(pattern)

        return patterns

    def _laplace_noise(self, epsilon: float) -> float:
        """Generate Laplacian noise for differential privacy.

        Args:
            epsilon: Privacy parameter (smaller = more privacy).

        Returns:
            Noise value.
        """
        # Laplace distribution: scale = 1/epsilon
        scale = 1.0 / epsilon
        u = random.uniform(-0.5, 0.5)
        return -scale * random.choice([1, -1]) * math.log(1 - 2 * abs(u))

    def _get_timestamp(self) -> str:
        """Get current UTC timestamp."""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()

    def get_aggregate_patterns(self, min_simulations: int = 10) -> dict[str, Any]:
        """Get aggregated patterns across opted-in simulations.

        Args:
            min_simulations: Minimum number of simulations for a pattern to be included.

        Returns:
            Aggregated patterns with confidence metrics.
        """
        result = {
            "total_simulations": len(_opted_in_simulations),
            "patterns": {},
        }

        # Check if we have enough simulations
        if len(_opted_in_simulations) < min_simulations:
            result["warning"] = (
                f"Insufficient simulations ({len(_opted_in_simulations)}/{min_simulations}) for reliable patterns"
            )
            return result

        # Aggregate archetype decision patterns
        archetype_stats: dict[str, list[float]] = defaultdict(list)
        for pattern in _aggregate_patterns.get("archetype_decision_frequency", []):
            archetype_stats[pattern["archetype_id"]].append(pattern["support_rate"])

        result["patterns"]["archetype_decisions"] = {}
        for archetype_id, rates in archetype_stats.items():
            if len(rates) >= min_simulations // 2:  # At least half must have this archetype
                avg_rate = sum(rates) / len(rates)
                result["patterns"]["archetype_decisions"][archetype_id] = {
                    "average_support_rate": round(avg_rate, 3),
                    "sample_size": len(rates),
                    "confidence": min(1.0, len(rates) / min_simulations),
                }

        # Aggregate coalition patterns
        coalition_stats: dict[str, int] = defaultdict(int)
        for pattern in _aggregate_patterns.get("coalition_formation", []):
            coalition_stats[pattern["archetype_pair"]] += pattern["frequency"]

        result["patterns"]["coalition_formations"] = {
            pair: {"frequency": freq}
            for pair, freq in sorted(coalition_stats.items(), key=lambda x: x[1], reverse=True)[:10]  # Top 10
        }

        # Aggregate environment outcomes
        env_stats: dict[str, dict] = defaultdict(lambda: {"rounds": [], "consensus": 0, "total": 0})
        for pattern in _aggregate_patterns.get("environment_outcome", []):
            env = pattern["environment"]
            env_stats[env]["rounds"].append(pattern["rounds_to_completion"])
            env_stats[env]["total"] += 1
            if pattern.get("consensus_reached"):
                env_stats[env]["consensus"] += 1

        result["patterns"]["environment_outcomes"] = {}
        for env, stats in env_stats.items():
            if stats["rounds"]:
                result["patterns"]["environment_outcomes"][env] = {
                    "average_rounds": round(sum(stats["rounds"]) / len(stats["rounds"]), 1),
                    "consensus_rate": (round(stats["consensus"] / stats["total"], 3) if stats["total"] > 0 else 0),
                    "sample_size": stats["total"],
                }

        return result

    def get_privacy_report(self, simulation_id: str) -> dict[str, Any]:
        """Get a privacy report showing what data was shared.

        Args:
            simulation_id: ID of the simulation.

        Returns:
            Privacy report with details of shared data.
        """
        if simulation_id not in _opted_in_simulations:
            return {
                "simulation_id": simulation_id,
                "opted_in": False,
                "data_points_shared": 0,
            }

        stored = _pattern_store.get(simulation_id, {})
        patterns = stored.get("patterns", [])

        # Categorize patterns
        categories: dict[str, int] = defaultdict(int)
        for pattern in patterns:
            categories[pattern.get("pattern_type", "unknown")] += 1

        return {
            "simulation_id": simulation_id,
            "opted_in": True,
            "data_points_shared": len(patterns),
            "categories": dict(categories),
            "anonymization_method": "differential_privacy_laplace_noise",
            "privacy_epsilon": self.privacy_epsilon,
            "shared_at": stored.get("extracted_at"),
            "note": "All data is anonymized and aggregated. Individual agent identities are never shared.",
        }

    def improve_archetypes(self, patterns: dict) -> dict[str, Any]:
        """Suggest archetype parameter adjustments based on aggregate data.

        Args:
            patterns: Aggregated patterns from get_aggregate_patterns.

        Returns:
            Suggested improvements per archetype.
        """
        suggestions = {}

        archetype_decisions = patterns.get("patterns", {}).get("archetype_decisions", {})
        for archetype_id, stats in archetype_decisions.items():
            if stats["confidence"] >= 0.5:  # Only suggest if confident
                avg_support = stats["average_support_rate"]

                # Suggest aggression level adjustment
                if avg_support > 0.7:
                    suggestions[archetype_id] = {
                        "parameter": "aggression_level",
                        "suggested_value": round(avg_support, 2),
                        "current_estimate": 0.5,
                        "confidence": stats["confidence"],
                        "sample_size": stats["sample_size"],
                        "rationale": "Archetype shows high support tendency across simulations",
                    }
                elif avg_support < 0.3:
                    suggestions[archetype_id] = {
                        "parameter": "skepticism_level",
                        "suggested_value": round(1 - avg_support, 2),
                        "current_estimate": 0.5,
                        "confidence": stats["confidence"],
                        "sample_size": stats["sample_size"],
                        "rationale": "Archetype shows high opposition tendency across simulations",
                    }

        return suggestions


# Global instance
cross_simulation_learner = CrossSimulationLearner()
