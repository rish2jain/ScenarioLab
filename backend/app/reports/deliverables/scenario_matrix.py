"""Helper functions for scenario matrix construction."""

import logging
from typing import Any

from app.simulation.models import RoundState

logger = logging.getLogger(__name__)


# Keywords indicating decision points
DECISION_KEYWORDS = [
    "decide",
    "decision",
    "vote",
    "proposal",
    "propose",
    "agree",
    "consensus",
    "approve",
    "reject",
    "accept",
    "choose",
    "option",
    "alternative",
    "path",
    "direction",
]

# Outcome dimension categories
OUTCOME_DIMENSIONS = [
    "Financial Performance",
    "Market Position",
    "Operational Efficiency",
    "Stakeholder Satisfaction",
    "Risk Exposure",
    "Strategic Alignment",
]


def identify_decision_branches(
    rounds: list[RoundState],
) -> list[dict[str, Any]]:
    """Identify decision branch points from simulation rounds.

    Analyzes rounds to find key decisions, votes, and turning points
    that could lead to different outcomes.

    Args:
        rounds: All round states from the simulation

    Returns:
        List of decision branch dictionaries
    """
    branches = []

    for round_state in rounds:
        round_num = round_state.round_number

        # Analyze messages for decision indicators
        decision_messages = []
        for msg in round_state.messages:
            content_lower = msg.content.lower()
            if any(kw in content_lower for kw in DECISION_KEYWORDS):
                decision_messages.append(msg)

        # Check for explicit decisions in round decisions
        round_decisions = round_state.decisions

        if decision_messages or round_decisions:
            branch = {
                "round": round_num,
                "phase": round_state.phase,
                "messages": decision_messages,
                "decisions": round_decisions,
                "message_count": len(round_state.messages),
            }
            branches.append(branch)

    logger.info(f"Identified {len(branches)} decision branches")
    return branches


def construct_scenario_narratives(
    branches: list[dict[str, Any]],
    total_rounds: int,
) -> list[dict[str, Any]]:
    """Construct scenario narratives from decision branches.

    Creates 3-5 distinct scenarios based on different combinations
    of decision outcomes.

    Args:
        branches: Decision branches identified from simulation
        total_rounds: Total number of rounds in simulation

    Returns:
        List of scenario narrative dictionaries
    """
    scenarios = []

    if not branches:
        # Create a baseline scenario if no branches found
        scenarios.append(
            {
                "name": "Baseline Scenario",
                "description": "Simulation proceeded without major disruptions " "or significant decision points.",
                "key_decisions": [],
                "outcome_path": "neutral",
            }
        )
        return scenarios

    # Scenario 1: Optimistic (favorable decisions)
    optimistic_decisions = _select_favorable_decisions(branches)
    scenarios.append(
        {
            "name": "Optimistic Scenario",
            "description": _build_scenario_description("optimistic", optimistic_decisions),
            "key_decisions": [b["round"] for b in optimistic_decisions],
            "outcome_path": "positive",
        }
    )

    # Scenario 2: Pessimistic (unfavorable decisions)
    pessimistic_decisions = _select_unfavorable_decisions(branches)
    scenarios.append(
        {
            "name": "Pessimistic Scenario",
            "description": _build_scenario_description("pessimistic", pessimistic_decisions),
            "key_decisions": [b["round"] for b in pessimistic_decisions],
            "outcome_path": "negative",
        }
    )

    # Scenario 3: Most Likely (middle ground)
    likely_decisions = _select_likely_decisions(branches)
    scenarios.append(
        {
            "name": "Most Likely Scenario",
            "description": _build_scenario_description("likely", likely_decisions),
            "key_decisions": [b["round"] for b in likely_decisions],
            "outcome_path": "neutral",
        }
    )

    # Scenario 4: Delayed/Prolonged (if enough rounds)
    if total_rounds > 5:
        scenarios.append(
            {
                "name": "Delayed Resolution Scenario",
                "description": "Key decisions are postponed or require multiple "
                "rounds of negotiation, leading to extended timelines "
                "and increased uncertainty.",
                "key_decisions": [b["round"] for b in branches[-2:]],
                "outcome_path": "delayed",
            }
        )

    # Scenario 5: Coalition Breakdown (if coalition dynamics detected)
    if _detect_coalition_dynamics(branches):
        scenarios.append(
            {
                "name": "Coalition Breakdown Scenario",
                "description": "Existing alliances fracture under pressure, "
                "leading to fragmented decision-making and "
                "inconsistent outcomes.",
                "key_decisions": [b["round"] for b in branches[:2]],
                "outcome_path": "fragmented",
            }
        )

    logger.info(f"Constructed {len(scenarios)} scenario narratives")
    return scenarios


def _select_favorable_decisions(branches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select decisions that would lead to favorable outcomes."""
    favorable = []
    for branch in branches:
        # Look for consensus or agreement indicators
        has_consensus = any(
            "agree" in m.content.lower() or "consensus" in m.content.lower() for m in branch.get("messages", [])
        )
        if has_consensus:
            favorable.append(branch)
    return favorable or branches[:2]


def _select_unfavorable_decisions(branches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select decisions that would lead to unfavorable outcomes."""
    unfavorable = []
    for branch in branches:
        # Look for rejection or conflict indicators
        has_conflict = any(
            "reject" in m.content.lower() or "oppose" in m.content.lower() or "disagree" in m.content.lower()
            for m in branch.get("messages", [])
        )
        if has_conflict:
            unfavorable.append(branch)
    return unfavorable or branches[-2:]


def _select_likely_decisions(branches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select decisions representing the most likely path."""
    # Take middle portion of branches
    mid = len(branches) // 2
    return branches[mid : mid + 2] if len(branches) > 2 else branches


def _detect_coalition_dynamics(branches: list[dict[str, Any]]) -> bool:
    """Detect if coalition dynamics were present in the simulation."""
    for branch in branches:
        for msg in branch.get("messages", []):
            content = msg.content.lower()
            if any(kw in content for kw in ["coalition", "alliance", "faction"]):
                return True
    return False


def _build_scenario_description(
    scenario_type: str,
    decisions: list[dict[str, Any]],
) -> str:
    """Build a description for a scenario based on type and decisions."""
    if not decisions:
        return f"No significant {scenario_type} decision points identified."

    decision_rounds = [str(d["round"]) for d in decisions]
    rounds_text = ", ".join(decision_rounds)

    descriptions = {
        "optimistic": (
            f"Favorable outcomes emerge from key decisions in rounds "
            f"{rounds_text}. Stakeholder alignment enables swift "
            f"implementation with minimal resistance."
        ),
        "pessimistic": (
            f"Challenges arise from contested decisions in rounds "
            f"{rounds_text}. Opposition and misalignment create "
            f"delays and suboptimal outcomes."
        ),
        "likely": (
            f"Moderate outcomes result from balanced decision-making "
            f"in rounds {rounds_text}. Mixed stakeholder support "
            f"leads to compromises and incremental progress."
        ),
    }

    default_desc = f"Scenario based on rounds {rounds_text}"
    return descriptions.get(scenario_type, default_desc)


def calculate_probability_ranges(
    scenario: dict[str, Any],
    all_branches: list[dict[str, Any]],
) -> tuple[float, float]:
    """Calculate probability range for a scenario.

    Args:
        scenario: The scenario to calculate probability for
        all_branches: All decision branches for context

    Returns:
        Tuple of (min_probability, max_probability)
    """
    outcome_path = scenario.get("outcome_path", "neutral")

    # Base probabilities by scenario type
    base_ranges = {
        "positive": (0.25, 0.40),
        "negative": (0.15, 0.30),
        "neutral": (0.30, 0.50),
        "delayed": (0.10, 0.25),
        "fragmented": (0.05, 0.20),
    }

    min_prob, max_prob = base_ranges.get(outcome_path, (0.20, 0.40))

    # Adjust based on number of key decisions
    key_decisions = scenario.get("key_decisions", [])
    if len(key_decisions) > 3:
        # More decisions = narrower range (more certainty)
        max_prob -= 0.05
    elif len(key_decisions) < 2:
        # Fewer decisions = wider range (more uncertainty)
        max_prob += 0.05

    # Ensure valid range
    max_prob = max(max_prob, min_prob + 0.05)
    max_prob = min(max_prob, 1.0)
    min_prob = max(min_prob, 0.0)

    return (round(min_prob, 2), round(max_prob, 2))


def get_outcome_dimensions() -> list[str]:
    """Get the standard outcome dimensions for scenario analysis."""
    return OUTCOME_DIMENSIONS.copy()
