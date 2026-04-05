"""Helper functions for risk register analysis."""

import logging
import re
from typing import Any

from app.simulation.models import AgentState, SimulationMessage

logger = logging.getLogger(__name__)


# Risk signal keywords for detection
RISK_KEYWORDS = {
    "objection": ["object", "oppose", "disagree", "concern", "against"],
    "conflict": ["conflict", "dispute", "clash", "disagreement", "tension"],
    "failure": ["fail", "unsuccessful", "rejected", "denied", "blocked"],
    "threat": ["threat", "risk", "danger", "jeopardy", "vulnerable"],
    "uncertainty": ["uncertain", "unknown", "unclear", "ambiguous", "unpredictable"],
}

IMPACT_INDICATORS = {
    "critical": ["catastrophic", "disaster", "collapse", "fatal", "existential"],
    "high": ["severe", "significant", "major", "serious", "substantial"],
    "medium": ["moderate", "notable", "considerable", "meaningful"],
    "low": ["minor", "small", "limited", "negligible", "trivial"],
}


def extract_risk_signals(
    messages: list[SimulationMessage],
    agent_states: list[AgentState],
) -> list[dict[str, Any]]:
    """Extract risk signals from simulation messages.

    Analyzes messages for objections, conflicts, failed proposals,
    and other risk indicators.

    Args:
        messages: All messages from the simulation
        agent_states: Final states of all agents

    Returns:
        List of risk signal dictionaries
    """
    signals = []

    for msg in messages:
        content_lower = msg.content.lower()

        # Check for objection signals
        if msg.message_type == "objection" or any(kw in content_lower for kw in RISK_KEYWORDS["objection"]):
            signals.append(
                {
                    "type": "objection",
                    "agent": msg.agent_name,
                    "content": msg.content,
                    "round": msg.round_number,
                    "confidence": 0.8 if msg.message_type == "objection" else 0.5,
                }
            )

        # Check for conflict signals
        if any(kw in content_lower for kw in RISK_KEYWORDS["conflict"]):
            signals.append(
                {
                    "type": "conflict",
                    "agent": msg.agent_name,
                    "content": msg.content,
                    "round": msg.round_number,
                    "confidence": 0.7,
                }
            )

        # Check for failure signals
        if any(kw in content_lower for kw in RISK_KEYWORDS["failure"]):
            signals.append(
                {
                    "type": "failure",
                    "agent": msg.agent_name,
                    "content": msg.content,
                    "round": msg.round_number,
                    "confidence": 0.6,
                }
            )

        # Check for threat signals
        if any(kw in content_lower for kw in RISK_KEYWORDS["threat"]):
            signals.append(
                {
                    "type": "threat",
                    "agent": msg.agent_name,
                    "content": msg.content,
                    "round": msg.round_number,
                    "confidence": 0.7,
                }
            )

    # Analyze agent stances for disagreements
    stance_conflicts = _detect_stance_conflicts(agent_states)
    signals.extend(stance_conflicts)

    logger.info(f"Extracted {len(signals)} risk signals from simulation")
    return signals


def _detect_stance_conflicts(
    agent_states: list[AgentState],
) -> list[dict[str, Any]]:
    """Detect conflicts based on agent stance differences."""
    conflicts = []

    # Group agents by coalition membership
    coalition_groups: dict[str, list[str]] = {}
    for agent in agent_states:
        for coalition in agent.coalition_members:
            if coalition not in coalition_groups:
                coalition_groups[coalition] = []
            coalition_groups[coalition].append(agent.name)

    # Check for agents in opposing coalitions
    for agent in agent_states:
        if agent.coalition_members:
            # Check for agents not in same coalition
            for other in agent_states:
                if other.id != agent.id:
                    shared_coalitions = set(agent.coalition_members) & set(other.coalition_members)
                    if not shared_coalitions:
                        conflicts.append(
                            {
                                "type": "coalition_conflict",
                                "agent": agent.name,
                                "content": f"Potential conflict: {agent.name} and "
                                f"{other.name} are in opposing coalitions",
                                "round": 0,
                                "confidence": 0.6,
                            }
                        )

    return conflicts


def score_risk_probability(
    signal: dict[str, Any],
    all_messages: list[SimulationMessage],
) -> float:
    """Score the probability of a risk based on signal strength and frequency.

    Args:
        signal: The risk signal to score
        all_messages: All messages for context

    Returns:
        Probability score between 0.0 and 1.0
    """
    base_score = signal.get("confidence", 0.5)

    # Adjust based on signal type
    type_weights = {
        "objection": 0.7,
        "conflict": 0.8,
        "failure": 0.9,
        "threat": 0.75,
        "coalition_conflict": 0.6,
    }
    signal_type = signal.get("type", "unknown")
    type_weight = type_weights.get(signal_type, 0.5)

    # Check for repeated mentions (increases probability)
    content_keywords = signal.get("content", "").lower().split()
    repeat_count = 0
    for msg in all_messages:
        if any(kw in msg.content.lower() for kw in content_keywords[:3]):
            repeat_count += 1

    repetition_boost = min(repeat_count * 0.05, 0.2)  # Max 0.2 boost

    probability = (base_score * type_weight) + repetition_boost
    return min(max(probability, 0.0), 1.0)


def score_risk_impact(content: str) -> str:
    """Score the impact level of a risk based on content analysis.

    Args:
        content: The risk description or signal content

    Returns:
        Impact level: "low", "medium", "high", or "critical"
    """
    content_lower = content.lower()

    # Check for critical indicators
    if any(kw in content_lower for kw in IMPACT_INDICATORS["critical"]):
        return "critical"

    # Check for high impact indicators
    if any(kw in content_lower for kw in IMPACT_INDICATORS["high"]):
        return "high"

    # Check for medium impact indicators
    if any(kw in content_lower for kw in IMPACT_INDICATORS["medium"]):
        return "medium"

    # Default to low if no strong indicators
    return "low"


def identify_risk_owner(
    signal: dict[str, Any],
    agent_states: list[AgentState],
) -> str:
    """Identify the risk owner based on the signal and agent roles.

    Args:
        signal: The risk signal
        agent_states: All agent states

    Returns:
        Name of the agent/role responsible for the risk
    """
    # If signal has an associated agent, they may be the owner
    signal_agent = signal.get("agent", "")

    # Find the agent in states
    for agent in agent_states:
        if agent.name == signal_agent:
            # Check if this agent raised the concern (not necessarily owner)
            if signal.get("type") == "objection":
                # The objector might be highlighting someone else's risk
                return _find_related_owner(signal, agent_states) or agent.name
            return agent.name

    # Fallback: try to extract from content
    return _find_related_owner(signal, agent_states) or "Unassigned"


def _find_related_owner(
    signal: dict[str, Any],
    agent_states: list[AgentState],
) -> str | None:
    """Try to find a related owner from signal content."""
    content = signal.get("content", "")

    # Look for mentions of other agents
    for agent in agent_states:
        if agent.name in content and agent.name != signal.get("agent", ""):
            return agent.name

    # Look for role-based patterns
    role_patterns = [
        r"(?:CFO|CEO|CTO|COO|CMO|CHRO)",
        r"(?:Director|VP|Head|Manager) of \w+",
        r"(?:Finance|Operations|Tech|Marketing|HR) (?:Lead|Head)",
    ]

    for pattern in role_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(0)

    return None
