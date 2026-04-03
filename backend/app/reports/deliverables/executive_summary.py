"""Helper functions for executive summary generation."""

import logging
from typing import Any

from app.simulation.models import AgentState, RoundState, SimulationMessage

logger = logging.getLogger(__name__)


# Key finding indicators
FINDING_INDICATORS = {
    "consensus": ["consensus", "agreement", "aligned", "unanimous"],
    "conflict": ["disagreement", "conflict", "divided", "opposition"],
    "breakthrough": ["breakthrough", "solution", "resolved", "success"],
    "deadlock": ["deadlock", "stalemate", "impasse", "gridlock"],
    "concern": ["concern", "risk", "issue", "problem", "challenge"],
}


def extract_key_findings(
    messages: list[SimulationMessage],
    rounds: list[RoundState],
    agent_states: list[AgentState],
) -> list[str]:
    """Extract key findings from the simulation.

    Analyzes messages, decisions, and agent states to identify
    the most significant outcomes and patterns.

    Args:
        messages: All simulation messages
        rounds: All round states
        agent_states: Final agent states

    Returns:
        List of key finding strings
    """
    findings = []

    # 1. Analyze for consensus or conflict
    consensus_level = _analyze_consensus(messages)
    if consensus_level > 0.7:
        findings.append(
            "Strong consensus emerged among stakeholders on key decisions"
        )
    elif consensus_level < 0.3:
        findings.append(
            "Significant disagreement persisted throughout the simulation"
        )
    else:
        findings.append(
            "Mixed alignment with partial consensus on some issues"
        )

    # 2. Check for decisive moments
    decisive_rounds = _identify_decisive_rounds(rounds)
    if decisive_rounds:
        findings.append(
            f"Critical turning points occurred in rounds "
            f"{', '.join(str(r) for r in decisive_rounds[:3])}"
        )

    # 3. Analyze coalition dynamics
    coalitions = _analyze_coalitions(agent_states)
    if coalitions:
        findings.append(
            f"{len(coalitions)} distinct coalitions formed during "
            f"the simulation, influencing decision outcomes"
        )

    # 4. Check for unresolved issues
    unresolved = _identify_unresolved_issues(messages, agent_states)
    if unresolved:
        findings.append(
            f"{len(unresolved)} significant issues remained unresolved "
            f"at simulation conclusion"
        )

    # 5. Analyze participation patterns
    participation = _analyze_participation(messages, agent_states)
    if participation["dominant"]:
        findings.append(
            f"{participation['dominant'][0]} emerged as the most "
            f"influential voice in discussions"
        )

    logger.info(f"Extracted {len(findings)} key findings")
    return findings


def rank_recommendations(
    findings: list[str],
    risk_items: list[dict[str, Any]],
    agent_states: list[AgentState],
) -> list[dict[str, Any]]:
    """Rank recommendations by impact and urgency.

    Args:
        findings: Key findings from simulation
        risk_items: Identified risk items
        agent_states: Agent states

    Returns:
        List of ranked recommendation dictionaries
    """
    recommendations = []

    # Generate recommendations based on findings
    for finding in findings:
        finding_lower = finding.lower()

        if "consensus" in finding_lower and "strong" in finding_lower:
            recommendations.append({
                "title": "Leverage Existing Alignment",
                "description": (
                    "Build on the strong consensus achieved to drive "
                    "rapid implementation of agreed initiatives"
                ),
                "priority": "high",
                "rationale": (
                    "Window of alignment may close; act while "
                    "stakeholder support is strong"
                ),
            })

        if "disagreement" in finding_lower or "conflict" in finding_lower:
            recommendations.append({
                "title": "Address Core Divisions",
                "description": (
                    "Facilitate targeted mediation sessions to resolve "
                    "fundamental disagreements before proceeding"
                ),
                "priority": "high",
                "rationale": (
                    "Unaddressed conflicts will resurface during "
                    "implementation and derail progress"
                ),
            })

        if "coalition" in finding_lower:
            recommendations.append({
                "title": "Engage Coalition Leaders",
                "description": (
                    "Work with coalition leaders to align interests "
                    "and build broader consensus"
                ),
                "priority": "medium",
                "rationale": (
                    "Coalition dynamics will shape implementation; "
                    "early engagement is critical"
                ),
            })

    # Add recommendations based on risks
    critical_risks = [r for r in risk_items if r.get("impact") == "critical"]
    high_risks = [r for r in risk_items if r.get("impact") == "high"]

    if critical_risks:
        recommendations.append({
            "title": "Mitigate Critical Risks",
            "description": (
                f"Immediately address {len(critical_risks)} critical "
                f"risk(s) identified in the simulation"
            ),
            "priority": "high",
            "rationale": (
                "Critical risks have potential for severe negative impact"
            ),
        })

    if high_risks:
        recommendations.append({
            "title": "Develop Risk Response Plan",
            "description": (
                f"Create detailed mitigation plans for {len(high_risks)} "
                f"high-impact risks"
            ),
            "priority": "medium",
            "rationale": (
                "Proactive risk management will improve outcome predictability"
            ),
        })

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    recommendations.sort(
        key=lambda x: priority_order.get(x["priority"], 3)
    )

    # Limit to top 3
    return recommendations[:3]


def format_for_presentation(
    text: str,
    max_length: int = 2000,
) -> str:
    """Format text for consulting presentation style.

    Args:
        text: Raw text to format
        max_length: Maximum length in characters

    Returns:
        Formatted text
    """
    # Ensure proper paragraph breaks
    formatted = text.replace("\n\n\n", "\n\n")

    # Ensure bullet points are properly formatted
    lines = formatted.split("\n")
    formatted_lines = []

    for line in lines:
        stripped = line.strip()
        # Convert dash bullets to standard format
        if stripped.startswith("- ") or stripped.startswith("* "):
            formatted_lines.append("• " + stripped[2:])
        else:
            formatted_lines.append(line)

    formatted = "\n".join(formatted_lines)

    # Truncate if needed
    if len(formatted) > max_length:
        formatted = formatted[:max_length-3] + "..."

    return formatted


def _analyze_consensus(messages: list[SimulationMessage]) -> float:
    """Analyze level of consensus in messages (0.0 to 1.0)."""
    if not messages:
        return 0.5

    consensus_count = 0
    conflict_count = 0

    for msg in messages:
        content_lower = msg.content.lower()
        if any(kw in content_lower for kw in FINDING_INDICATORS["consensus"]):
            consensus_count += 1
        if any(kw in content_lower for kw in FINDING_INDICATORS["conflict"]):
            conflict_count += 1

    total = consensus_count + conflict_count
    if total == 0:
        return 0.5

    return consensus_count / total


def _identify_decisive_rounds(rounds: list[RoundState]) -> list[int]:
    """Identify rounds with decisive moments."""
    decisive = []

    for round_state in rounds:
        # Check for votes or major decisions
        if round_state.decisions:
            decisive.append(round_state.round_number)
            continue

        # Check for breakthrough or deadlock indicators
        for msg in round_state.messages:
            content_lower = msg.content.lower()
            if any(
                kw in content_lower
                for kw in FINDING_INDICATORS["breakthrough"]
                + FINDING_INDICATORS["deadlock"]
            ):
                decisive.append(round_state.round_number)
                break

    return decisive


def _analyze_coalitions(
    agent_states: list[AgentState],
) -> list[dict[str, Any]]:
    """Analyze coalition formations."""
    coalition_map: dict[str, list[str]] = {}

    for agent in agent_states:
        for coalition in agent.coalition_members:
            if coalition not in coalition_map:
                coalition_map[coalition] = []
            coalition_map[coalition].append(agent.name)

    return [
        {"name": name, "members": members}
        for name, members in coalition_map.items()
        if len(members) > 1
    ]


def _identify_unresolved_issues(
    messages: list[SimulationMessage],
    agent_states: list[AgentState],
) -> list[str]:
    """Identify issues that remained unresolved."""
    unresolved = []

    # Look for concern indicators in later messages
    late_messages = messages[-10:] if len(messages) > 10 else messages

    for msg in late_messages:
        content_lower = msg.content.lower()
        if any(kw in content_lower for kw in FINDING_INDICATORS["concern"]):
            if len(msg.content) > 50:
                issue = msg.content[:50] + "..."
            else:
                issue = msg.content
            if issue not in unresolved:
                unresolved.append(issue)

    return unresolved[:5]  # Limit to top 5


def _analyze_participation(
    messages: list[SimulationMessage],
    agent_states: list[AgentState],
) -> dict[str, Any]:
    """Analyze participation patterns."""
    message_counts = {}

    for msg in messages:
        agent_id = msg.agent_id
        message_counts[agent_id] = message_counts.get(agent_id, 0) + 1

    if not message_counts:
        return {"dominant": None}

    # Find most active participant
    dominant_id = max(message_counts, key=message_counts.get)
    dominant_agent = next(
        (a for a in agent_states if a.id == dominant_id), None
    )

    return {
        "dominant": [dominant_agent.name] if dominant_agent else ["Unknown"],
        "counts": message_counts,
    }
