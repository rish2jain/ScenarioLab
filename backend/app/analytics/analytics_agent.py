"""Silent monitoring agent that extracts quantitative metrics."""

import logging
import re
from collections import Counter

from pydantic import BaseModel

from app.simulation.models import (
    AgentState,
    RoundState,
    SimulationMessage,
    SimulationState,
)

logger = logging.getLogger(__name__)


class SimulationMetrics(BaseModel):
    """Comprehensive metrics extracted from a simulation."""
    simulation_id: str
    # % of actions violating stated policies
    compliance_violation_rate: float
    # Rounds to reach decision, None if no consensus
    time_to_consensus: int | None
    # [{round: 1, positive: 0.4, negative: 0.3, neutral: 0.3}, ...]
    sentiment_trajectory: list[dict]
    # {role: divergence_score}
    role_polarization_index: dict[str, float]
    # % of proposed initiatives accepted
    policy_adoption_rate: float
    # [{round: N, members: [...], topic: "..."}]
    coalition_formation_events: list[dict]
    # [{round: N, description: "...", impact: "high/medium/low"}]
    key_turning_points: list[dict]
    # {agent_id: activity_level}
    agent_activity_scores: dict[str, float]
    # [{decision: "...", result: "approved/rejected", round: N}]
    decision_outcomes: list[dict]


class AnalyticsAgent:
    """Silent monitoring agent that extracts metrics."""

    # Sentiment keyword lists for simple analysis
    POSITIVE_WORDS = {
        "agree", "support", "approve", "accept", "favor", "positive", "benefit",
        "advantage", "improve", "success", "effective", "efficient", "optimal",
        "excellent", "good", "great", "best", "ideal", "recommend", "endorse",
        "confident", "optimistic", "progress", "gain", "win", "solution",
        "opportunity", "growth", "innovation", "strength", "asset", "value"
    }

    NEGATIVE_WORDS = {
        "disagree", "oppose", "reject", "deny", "refuse", "negative", "risk",
        "disadvantage", "worsen", "failure", "ineffective", "inefficient",
        "poor", "bad", "worst", "problem", "issue", "concern", "worry",
        "doubt", "skeptical", "pessimistic", "loss", "lose", "threat",
        "weakness", "liability", "cost", "burden", "challenge", "obstacle",
        "barrier", "resistance", "objection", "criticism", "flaw", "defect"
    }

    # Proposal-related patterns
    PROPOSAL_PATTERNS = [
        r"propose\w*\s+(?:that\s+)?(?:we\s+)?(.{10,100}?)(?:\.|$|\n)",
        r"suggest\w*\s+(?:that\s+)?(?:we\s+)?(.{10,100}?)(?:\.|$|\n)",
        r"recommend\w*\s+(?:that\s+)?(?:we\s+)?(.{10,100}?)(?:\.|$|\n)",
        r"move\s+(?:that\s+)?(?:we\s+)?(.{10,100}?)(?:\.|$|\n)",
    ]

    # Decision patterns
    APPROVAL_PATTERNS = [
        r"(?:approved?|accepted?|adopted?|agreed?|passed)",
        r"(?:we\s+(?:will|shall)\s+(?:proceed|move\s+forward|implement))",
        r"(?:consensus\s+(?:reached|achieved))",
        r"(?:unanimous\s+(?:support|approval))",
    ]

    REJECTION_PATTERNS = [
        r"(?:rejected?|denied?|declined?|opposed?|vetoed)",
        r"(?:we\s+(?:will\s+not|cannot)\s+(?:proceed|"
        r"move\s+forward|implement))",
        r"(?:no\s+(?:consensus|agreement))",
        r"(?:tabled?|postponed?|deferred)",
    ]

    def __init__(self, llm_provider=None):
        self.llm = llm_provider

    async def analyze_simulation(
        self, simulation_state: SimulationState
    ) -> SimulationMetrics:
        """Analyze a completed simulation and extract all metrics."""
        logger.info(
            f"Analyzing simulation: {simulation_state.config.id}"
        )

        # Gather all messages from all rounds
        all_messages: list[SimulationMessage] = []
        for round_state in simulation_state.rounds:
            all_messages.extend(round_state.messages)

        agents = simulation_state.agents
        rounds = simulation_state.rounds

        # Compute all metrics in parallel where possible
        compliance_rate = await self.compute_compliance_violations(
            all_messages, agents
        )
        time_to_consensus = await self.compute_time_to_consensus(rounds)
        sentiment_trajectory = await self.compute_sentiment_trajectory(rounds)
        polarization = await self.compute_polarization_index(
            agents, all_messages
        )
        adoption_rate = await self.compute_policy_adoption_rate(rounds)
        coalitions = await self.detect_coalitions(all_messages, agents)
        turning_points = await self.identify_turning_points(rounds)
        activity_scores = await self.compute_agent_activity_scores(
            all_messages, agents
        )
        decision_outcomes = await self.extract_decision_outcomes(rounds)

        metrics = SimulationMetrics(
            simulation_id=simulation_state.config.id,
            compliance_violation_rate=compliance_rate,
            time_to_consensus=time_to_consensus,
            sentiment_trajectory=sentiment_trajectory,
            role_polarization_index=polarization,
            policy_adoption_rate=adoption_rate,
            coalition_formation_events=coalitions,
            key_turning_points=turning_points,
            agent_activity_scores=activity_scores,
            decision_outcomes=decision_outcomes,
        )

        logger.info(
            f"Analysis complete for simulation: {simulation_state.config.id}"
        )
        return metrics

    async def compute_compliance_violations(
        self, messages: list[SimulationMessage], agents: list[AgentState]
    ) -> float:
        """Detect messages/actions that violate stated policies.

        Returns percentage of potentially non-compliant messages (0-100).
        """
        if not messages:
            return 0.0

        # Build agent policy map from archetype info
        agent_policies: dict[str, list[str]] = {}
        for agent in agents:
            # Extract policy constraints from persona prompt
            policies = self._extract_policies_from_prompt(agent.persona_prompt)
            agent_policies[agent.id] = policies

        violation_count = 0

        for msg in messages:
            agent_id = msg.agent_id
            content = msg.content.lower()

            # Check against agent's stated policies
            policies = agent_policies.get(agent_id, [])
            for policy in policies:
                # Simple keyword-based contradiction detection
                if self._is_contradictory(content, policy):
                    violation_count += 1
                    break

        # Return percentage of violations
        return round((violation_count / len(messages)) * 100, 2)

    def _extract_policies_from_prompt(self, prompt: str) -> list[str]:
        """Extract stated policies/constraints from agent persona prompt."""
        policies = []

        # Look for common policy indicators
        policy_patterns = [
            r"(?:you must|you should|always|never|priority|ensure|maintain)"
            r"\s+(.{10,150}?)(?:\.|$|\n)",
            r"(?:objective|goal|mandate|responsibility):?"
            r"\s*(.{10,150}?)(?:\.|$|\n)",
        ]

        prompt_lower = prompt.lower()
        for pattern in policy_patterns:
            matches = re.finditer(pattern, prompt_lower, re.IGNORECASE)
            for match in matches:
                policies.append(match.group(1).strip())

        return policies

    def _is_contradictory(self, content: str, policy: str) -> bool:
        """Simple heuristic to detect if content contradicts a policy."""
        # Very basic check: if policy says "never X" and content says "X"
        policy_words = set(policy.lower().split())
        content_words = set(content.lower().split())

        # Check for negation flips
        negation_words = {
            "never", "no", "not", "don't", "won't", "shouldn't", "mustn't"
        }
        has_policy_negation = bool(policy_words & negation_words)

        # Extract key policy terms (excluding common words)
        common_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "you", "must", "should", "always",
            "never",
        }
        key_terms = policy_words - common_words - negation_words

        if not key_terms:
            return False

        # Check if key terms appear in content
        content_has_terms = bool(key_terms & content_words)

        # Simple contradiction: policy says "never X" but content
        # mentions X positively
        if has_policy_negation and content_has_terms:
            # Check if content also has negation (aligns with policy)
            content_has_negation = bool(content_words & negation_words)
            if not content_has_negation:
                return True

        return False

    async def compute_time_to_consensus(
        self, rounds: list[RoundState]
    ) -> int | None:
        """Calculate rounds needed to reach decision/consensus."""
        if not rounds:
            return None

        for i, round_state in enumerate(rounds):
            # Check if this round had a clear decision
            for decision in round_state.decisions:
                evaluation = decision.get("evaluation", {})
                if evaluation.get("consensus_reached"):
                    return i + 1  # 1-indexed round number
                if evaluation.get("decision_made"):
                    return i + 1  # 1-indexed round number

            # Check messages for consensus indicators
            for msg in round_state.messages:
                content = msg.content.lower()
                if any(re.search(p, content) for p in self.APPROVAL_PATTERNS):
                    return i + 1

        return None  # No consensus reached

    async def compute_sentiment_trajectory(
        self, rounds: list[RoundState]
    ) -> list[dict]:
        """Track sentiment over time using keyword-based analysis."""
        trajectory = []

        for round_state in rounds:
            if not round_state.messages:
                trajectory.append({
                    "round": round_state.round_number,
                    "positive": 0.0,
                    "negative": 0.0,
                    "neutral": 1.0,
                })
                continue

            positive_count = 0
            negative_count = 0

            for msg in round_state.messages:
                content = msg.content.lower()
                words = set(re.findall(r'\b\w+\b', content))

                pos_matches = len(words & self.POSITIVE_WORDS)
                neg_matches = len(words & self.NEGATIVE_WORDS)

                # Simple scoring: net sentiment per message
                if pos_matches > neg_matches:
                    positive_count += 1
                elif neg_matches > pos_matches:
                    negative_count += 1

            total = len(round_state.messages)
            trajectory.append({
                "round": round_state.round_number,
                "positive": round(positive_count / total, 2),
                "negative": round(negative_count / total, 2),
                "neutral": round(
                    (total - positive_count - negative_count) / total, 2
                ),
            })

        return trajectory

    async def compute_polarization_index(
        self, agents: list[AgentState], messages: list[SimulationMessage]
    ) -> dict[str, float]:
        """Calculate alignment divergence by role."""
        if not agents or not messages:
            return {}

        # Group messages by agent role
        role_messages: dict[str, list[SimulationMessage]] = {}
        for msg in messages:
            role = msg.agent_role
            if role not in role_messages:
                role_messages[role] = []
            role_messages[role].append(msg)

        # Calculate average sentiment per role
        role_sentiments: dict[str, float] = {}
        for role, msgs in role_messages.items():
            total_sentiment = 0
            for msg in msgs:
                content = msg.content.lower()
                words = set(re.findall(r'\b\w+\b', content))
                pos_matches = len(words & self.POSITIVE_WORDS)
                neg_matches = len(words & self.NEGATIVE_WORDS)
                sentiment = (pos_matches - neg_matches) / max(len(words), 1)
                total_sentiment += sentiment

            role_sentiments[role] = total_sentiment / len(msgs) if msgs else 0

        # Calculate polarization as standard deviation from mean
        if len(role_sentiments) < 2:
            return {role: 0.0 for role in role_sentiments}

        sentiments = list(role_sentiments.values())
        mean_sentiment = sum(sentiments) / len(sentiments)

        # Calculate variance
        variance = sum(
            (s - mean_sentiment) ** 2 for s in sentiments
        ) / len(sentiments)
        std_dev = variance ** 0.5

        # Individual polarization scores (distance from mean, normalized)
        polarization = {}
        for role, sentiment in role_sentiments.items():
            distance = abs(sentiment - mean_sentiment)
            polarization[role] = round(
                min(distance / max(std_dev, 0.001), 2.0), 2
            )

        return polarization

    async def compute_policy_adoption_rate(
        self, rounds: list[RoundState]
    ) -> float:
        """Calculate % of proposals that were adopted."""
        proposals = []
        adoptions = []

        for round_state in rounds:
            for msg in round_state.messages:
                content = msg.content

                # Detect proposals
                for pattern in self.PROPOSAL_PATTERNS:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        proposals.append({
                            "text": match.group(1).strip(),
                            "round": round_state.round_number,
                        })

            # Check decisions for adoption
            for decision in round_state.decisions:
                evaluation = decision.get("evaluation", {})
                if evaluation.get("outcome") in [
                    "approved", "accepted", "adopted"
                ]:
                    adoptions.append(round_state.round_number)

        if not proposals:
            return 0.0

        # Count proposals that appear to have been adopted
        # (simplified: if any approval happened after proposal)
        adopted_count = 0
        for proposal in proposals:
            for adoption_round in adoptions:
                if adoption_round >= proposal["round"]:
                    adopted_count += 1
                    break

        return round((adopted_count / len(proposals)) * 100, 2)

    async def detect_coalitions(
        self, messages: list[SimulationMessage], agents: list[AgentState]
    ) -> list[dict]:
        """Detect coalition formation events."""
        coalitions = []

        # Group messages by round
        round_messages: dict[int, list[SimulationMessage]] = {}
        for msg in messages:
            rn = msg.round_number
            if rn not in round_messages:
                round_messages[rn] = []
            round_messages[rn].append(msg)

        # Detect coalition patterns per round
        for round_num, msgs in sorted(round_messages.items()):
            # Look for alignment patterns
            alignment_keywords = [
                "agree with", "support", "join", "together",
                "aligned", "same page", "united",
            ]

            # Track who aligns with whom
            alignments: dict[str, set[str]] = {}

            for msg in msgs:
                content_lower = msg.content.lower()
                agent_id = msg.agent_id

                for keyword in alignment_keywords:
                    if keyword in content_lower:
                        # Find who they're aligning with
                        for other_agent in agents:
                            if other_agent.id != agent_id:
                                name_lower = other_agent.name.lower()
                                if name_lower in content_lower:
                                    if agent_id not in alignments:
                                        alignments[agent_id] = set()
                                    alignments[agent_id].add(other_agent.id)

            # Identify coalition groups (3+ agents with mutual alignment)
            coalition_groups = self._find_coalition_groups(alignments)

            for group in coalition_groups:
                # Find coalition topic
                topic = self._extract_coalition_topic(msgs, group)

                coalitions.append({
                    "round": round_num,
                    "members": list(group),
                    "topic": topic,
                })

        return coalitions

    def _find_coalition_groups(
        self, alignments: dict[str, set[str]]
    ) -> list[set[str]]:
        """Find groups of 3+ mutually aligned agents."""
        groups = []
        processed = set()

        for agent_id, aligned_with in alignments.items():
            if agent_id in processed:
                continue

            # Build coalition group
            group = {agent_id}
            group.update(aligned_with)

            # Check for mutual alignment
            for other_id in list(aligned_with):
                if other_id in alignments:
                    if agent_id in alignments[other_id]:
                        group.update(alignments[other_id])

            if len(group) >= 3:
                groups.append(group)
                processed.update(group)

        return groups

    def _extract_coalition_topic(
        self, messages: list[SimulationMessage], coalition_members: set[str]
    ) -> str:
        """Extract the topic around which a coalition formed."""
        # Collect messages from coalition members
        member_msgs = [m for m in messages if m.agent_id in coalition_members]

        # Extract common keywords (excluding stop words)
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "is", "are", "was", "were", "be",
            "been", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "can",
            "this", "that", "these", "those", "i", "you", "he", "she",
            "it", "we", "they", "me", "him", "her", "us", "them", "my",
            "your", "his", "her", "its", "our", "their",
        }

        word_counts = Counter()
        for msg in member_msgs:
            words = re.findall(r'\b\w+\b', msg.content.lower())
            for word in words:
                if word not in stop_words and len(word) > 3:
                    word_counts[word] += 1

        # Return most common topic words
        top_words = [w for w, c in word_counts.most_common(3)]
        return " ".join(top_words) if top_words else "general alignment"

    async def identify_turning_points(
        self, rounds: list[RoundState]
    ) -> list[dict]:
        """Identify key turning points in the simulation."""
        turning_points = []

        if len(rounds) < 2:
            return turning_points

        # Analyze sentiment shifts between rounds
        sentiments = await self.compute_sentiment_trajectory(rounds)

        for i in range(1, len(sentiments)):
            prev = sentiments[i - 1]
            curr = sentiments[i]

            # Detect significant sentiment shifts
            pos_shift = curr["positive"] - prev["positive"]
            neg_shift = curr["negative"] - prev["negative"]

            if abs(pos_shift) > 0.3 or abs(neg_shift) > 0.3:
                # Determine impact level
                if abs(pos_shift) > 0.5 or abs(neg_shift) > 0.5:
                    impact = "high"
                elif abs(pos_shift) > 0.4 or abs(neg_shift) > 0.4:
                    impact = "medium"
                else:
                    impact = "low"

                # Generate description
                if pos_shift > 0:
                    description = (
                        f"Significant positive shift in sentiment "
                        f"(+{round(pos_shift * 100)}%)"
                    )
                else:
                    description = (
                        f"Significant negative shift in sentiment "
                        f"(+{round(abs(neg_shift) * 100)}%)"
                    )

                # Look for triggering event in messages
                round_state = rounds[i]
                if round_state.messages:
                    first_msg = round_state.messages[0]
                    description += f" triggered by {first_msg.agent_name}"

                turning_points.append({
                    "round": curr["round"],
                    "description": description,
                    "impact": impact,
                })

        # Check for decision points
        for round_state in rounds:
            for decision in round_state.decisions:
                evaluation = decision.get("evaluation", {})
                decision_made = evaluation.get("decision_made")
                consensus_reached = evaluation.get("consensus_reached")
                if decision_made or consensus_reached:
                    # Check if not already recorded
                    already_recorded = any(
                        tp["round"] == round_state.round_number
                        for tp in turning_points
                    )
                    if not already_recorded:
                        turning_points.append({
                            "round": round_state.round_number,
                            "description": "Key decision point reached",
                            "impact": "high",
                        })

        # Sort by round number
        turning_points.sort(key=lambda x: x["round"])

        return turning_points

    async def compute_agent_activity_scores(
        self, messages: list[SimulationMessage], agents: list[AgentState]
    ) -> dict[str, float]:
        """Calculate activity level for each agent."""
        if not agents:
            return {}

        # Count messages per agent
        message_counts: dict[str, int] = Counter()
        for msg in messages:
            message_counts[msg.agent_id] += 1

        # Calculate average message length as engagement indicator
        message_lengths: dict[str, list[int]] = {}
        for msg in messages:
            if msg.agent_id not in message_lengths:
                message_lengths[msg.agent_id] = []
            message_lengths[msg.agent_id].append(len(msg.content))

        # Compute activity scores (normalized 0-1)
        max_messages = max(message_counts.values()) if message_counts else 1

        activity_scores = {}
        for agent in agents:
            count = message_counts.get(agent.id, 0)
            lengths = message_lengths.get(agent.id, [0])
            avg_length = sum(lengths) / len(lengths) if lengths else 0

            # Combine message count and length into activity score
            normalized_count = count / max_messages if max_messages > 0 else 0
            normalized_length = min(avg_length / 500, 1.0)  # Cap at 500 chars

            activity_scores[agent.id] = round(
                (normalized_count * 0.7 + normalized_length * 0.3), 2
            )

        return activity_scores

    async def extract_decision_outcomes(
        self, rounds: list[RoundState]
    ) -> list[dict]:
        """Extract decision outcomes from rounds."""
        outcomes = []

        for round_state in rounds:
            for decision in round_state.decisions:
                evaluation = decision.get("evaluation", {})

                decision_text = evaluation.get("decision", "Unknown decision")
                outcome = evaluation.get("outcome", "unknown")

                # Normalize outcome
                approved = [
                    "approved", "accepted", "adopted", "passed", "for"
                ]
                rejected = [
                    "rejected", "denied", "declined", "opposed", "against"
                ]
                if outcome in approved:
                    result = "approved"
                elif outcome in rejected:
                    result = "rejected"
                else:
                    result = "pending"

                outcomes.append({
                    "decision": decision_text,
                    "result": result,
                    "round": round_state.round_number,
                })

        return outcomes
