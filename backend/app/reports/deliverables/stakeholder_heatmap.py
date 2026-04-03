"""Helper functions for stakeholder heatmap analysis."""

import logging
from typing import Any

from app.simulation.models import AgentState, RoundState, SimulationMessage

logger = logging.getLogger(__name__)


# Keywords indicating support/opposition
SUPPORT_KEYWORDS = [
    "support", "agree", "favor", "endorse", "back", "approve"
]
OPPOSITION_KEYWORDS = [
    "oppose", "against", "disagree", "reject", "block", "resist"
]
STRONG_MODIFIERS = [
    "strongly", "firmly", "absolutely", "completely", "totally"
]


def compute_support_levels(
    agent: AgentState,
    messages: list[SimulationMessage],
    rounds: list[RoundState],
) -> tuple[str, float]:
    """Compute support level for a stakeholder from their messages and votes.

    Args:
        agent: The agent state
        messages: All messages from the simulation
        rounds: All round states

    Returns:
        Tuple of (position_label, support_score)
    """
    agent_messages = [m for m in messages if m.agent_id == agent.id]

    if not agent_messages:
        return ("neutral", 0.0)

    # Analyze message sentiment
    support_count = 0
    oppose_count = 0
    strong_support = 0
    strong_oppose = 0

    for msg in agent_messages:
        content_lower = msg.content.lower()

        # Check for support indicators
        if any(kw in content_lower for kw in SUPPORT_KEYWORDS):
            support_count += 1
            if any(mod in content_lower for mod in STRONG_MODIFIERS):
                strong_support += 1

        # Check for opposition indicators
        if any(kw in content_lower for kw in OPPOSITION_KEYWORDS):
            oppose_count += 1
            if any(mod in content_lower for mod in STRONG_MODIFIERS):
                strong_oppose += 1

    # Analyze vote history
    for vote in agent.vote_history:
        vote_value = vote.get("vote", "").lower()
        if vote_value in ["for", "yes", "approve"]:
            support_count += 2  # Votes weighted more heavily
        elif vote_value in ["against", "no", "reject"]:
            oppose_count += 2

    # Calculate support score (-1.0 to 1.0)
    total_signals = support_count + oppose_count
    if total_signals == 0:
        return ("neutral", 0.0)

    raw_score = (support_count - oppose_count) / total_signals

    # Adjust for strong modifiers
    if strong_support > strong_oppose:
        raw_score = min(raw_score + 0.2, 1.0)
    elif strong_oppose > strong_support:
        raw_score = max(raw_score - 0.2, -1.0)

    # Determine position label
    if raw_score >= 0.7:
        position = "strongly_support"
    elif raw_score >= 0.3:
        position = "support"
    elif raw_score <= -0.7:
        position = "strongly_oppose"
    elif raw_score <= -0.3:
        position = "oppose"
    else:
        position = "neutral"

    return (position, round(raw_score, 2))


def calculate_influence_scores(
    agent: AgentState,
    all_agents: list[AgentState],
    messages: list[SimulationMessage],
) -> float:
    """Calculate influence score for a stakeholder.

    Based on authority level, coalition membership, message frequency,
    and how often others reference them.

    Args:
        agent: The agent state
        all_agents: All agent states
        messages: All messages

    Returns:
        Influence score between 0.0 and 1.0
    """
    score = 0.0

    # Base authority from archetype (assumed 0.5 if unknown)
    base_authority = 0.5
    score += base_authority * 0.3

    # Coalition membership bonus
    coalition_count = len(agent.coalition_members)
    if coalition_count > 0:
        score += min(coalition_count * 0.1, 0.2)

    # Message frequency (relative to average)
    agent_message_count = len([m for m in messages if m.agent_id == agent.id])
    avg_messages = len(messages) / max(len(all_agents), 1)
    if avg_messages > 0:
        freq_ratio = agent_message_count / avg_messages
        score += min(freq_ratio * 0.2, 0.3)

    # Referenced by others
    mention_count = 0
    for msg in messages:
        if agent.name in msg.content and msg.agent_id != agent.id:
            mention_count += 1
    score += min(mention_count * 0.05, 0.2)

    return round(min(score, 1.0), 2)


def identify_key_concerns(
    agent: AgentState,
    messages: list[SimulationMessage],
) -> list[str]:
    """Identify key concerns for a stakeholder from their messages.

    Args:
        agent: The agent state
        messages: All messages

    Returns:
        List of key concern strings
    """
    agent_messages = [m for m in messages if m.agent_id == agent.id]

    # Concern keywords
    concern_indicators = [
        "concern", "worry", "risk", "issue", "problem",
        "challenge", "threat", "afraid", "uncertain",
    ]

    concerns = []

    for msg in agent_messages:
        content = msg.content
        content_lower = content.lower()

        for indicator in concern_indicators:
            if indicator in content_lower:
                # Extract the sentence or phrase containing the concern
                concern = _extract_concern_phrase(content, indicator)
                if concern and concern not in concerns:
                    concerns.append(concern)

    # Limit to top 3 most significant concerns
    return concerns[:3]


def _extract_concern_phrase(content: str, indicator: str) -> str | None:
    """Extract a concise concern phrase from content."""
    # Simple extraction: find sentence containing indicator
    sentences = content.replace("!", ".").replace("?", ".").split(".")

    for sentence in sentences:
        if indicator in sentence.lower():
            # Clean up and truncate if needed
            phrase = sentence.strip()
            if len(phrase) > 100:
                phrase = phrase[:97] + "..."
            return phrase

    return None


def analyze_stance_changes(
    agent: AgentState,
    rounds: list[RoundState],
) -> list[dict[str, Any]]:
    """Analyze how a stakeholder's stance changed over time.

    Args:
        agent: The agent state
        rounds: All round states

    Returns:
        List of stance change events
    """
    changes = []
    prev_stance = None

    for round_state in rounds:
        round_msgs = [
            m for m in round_state.messages if m.agent_id == agent.id
        ]

        if not round_msgs:
            continue

        # Determine stance from messages in this round
        support = 0
        oppose = 0

        for msg in round_msgs:
            content_lower = msg.content.lower()
            if any(kw in content_lower for kw in SUPPORT_KEYWORDS):
                support += 1
            if any(kw in content_lower for kw in OPPOSITION_KEYWORDS):
                oppose += 1

        if support > oppose:
            current_stance = "supportive"
        elif oppose > support:
            current_stance = "opposed"
        else:
            current_stance = "neutral"

        if prev_stance and prev_stance != current_stance:
            changes.append({
                "round": round_state.round_number,
                "from": prev_stance,
                "to": current_stance,
            })

        prev_stance = current_stance

    return changes
