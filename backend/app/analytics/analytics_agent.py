"""Silent monitoring agent that extracts quantitative metrics."""

import asyncio
import json
import logging
import re
from collections import Counter
from typing import Any

from pydantic import BaseModel

from app.analytics.prompts import (
    ALIGNMENT_KEYWORDS,
    APPROVAL_PATTERNS,
    APPROVED_OUTCOMES,
    COALITION_STOP_WORDS,
    MIN_COALITION_SIZE,
    NEGATION_WORDS,
    NEGATIVE_WORDS,
    POLICY_EXTRACTION_PATTERNS,
    POSITIVE_WORDS,
    PROPOSAL_PATTERNS,
    REJECTED_OUTCOMES,
    REJECTION_PATTERNS,
    STOP_WORDS,
    TURNING_POINT_HIGH_THRESHOLD,
    TURNING_POINT_MEDIUM_THRESHOLD,
    TURNING_POINT_THRESHOLD,
)
from app.simulation.models import (
    AgentState,
    RoundState,
    SimulationMessage,
    SimulationState,
)

logger = logging.getLogger(__name__)


def _decision_meta_for_score(decision: dict[str, Any]) -> dict[str, Any]:
    """Merge round ``evaluation`` with top-level decision keys for scoring."""
    evaluation = decision.get("evaluation")
    meta: dict[str, Any] = dict(evaluation) if isinstance(evaluation, dict) else {}
    for k, v in decision.items():
        if k == "evaluation":
            continue
        if k not in meta:
            meta[k] = v
    if "vote_result" not in meta:
        res = decision.get("result")
        if isinstance(res, dict) and any(x in res for x in ("for", "against", "abstain", "total", "result")):
            meta["vote_result"] = res
    return meta


def _derive_decision_turning_point_score(decision: dict[str, Any]) -> float:
    """Score in ``[0, 1]`` from decision / evaluation metadata.

    Uses explicit ``importance``, vote margins / unanimity, consensus ratios,
    and boolean flags when present. Returns ``1.0`` when no usable signals exist
    (same as the previous fixed default).
    """
    meta = _decision_meta_for_score(decision)

    imp = meta.get("importance")
    if isinstance(imp, (int, float)):
        s = float(imp)
        if s <= 1.0:
            return round(max(0.0, min(1.0, s)), 2)
        if s <= 10.0:
            return round(min(1.0, s / 10.0), 2)
        return 1.0

    cc = meta.get("consensus_count")
    tot = meta.get("total_votes", meta.get("total_count", meta.get("total")))
    if isinstance(cc, (int, float)) and isinstance(tot, (int, float)) and tot > 0:
        return round(min(1.0, float(cc) / float(tot)), 2)

    # Prefer vote breakdown over coarse consensus flags when both exist.
    vr = meta.get("vote_result")
    if isinstance(vr, dict):
        total = vr.get("total")
        if isinstance(total, (int, float)) and total > 0:
            for_v = int(vr.get("for", 0) or 0)
            against_v = int(vr.get("against", 0) or 0)
            bloc = max(for_v, against_v)
            return round(min(1.0, float(bloc) / float(total)), 2)

    if meta.get("unanimity") is True or meta.get("unanimous") is True:
        return 1.0

    if meta.get("consensus_reached") is True:
        return 0.85
    if meta.get("agreement_reached") is True:
        return 0.9
    if meta.get("decision_made") is True:
        return 0.75

    return 1.0


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
    # [{round: N, description: "...", impact: "high/medium/low", score: float}]
    key_turning_points: list[dict]
    # {agent_id: activity_level}
    agent_activity_scores: dict[str, float]
    # [{decision: "...", result: "approved/rejected", round: N}]
    decision_outcomes: list[dict]


class AnalyticsAgent:
    """Silent monitoring agent that extracts metrics."""

    # Keep references as class attributes so existing callers that read
    # AnalyticsAgent.POSITIVE_WORDS etc. continue to work.
    POSITIVE_WORDS = POSITIVE_WORDS
    NEGATIVE_WORDS = NEGATIVE_WORDS
    PROPOSAL_PATTERNS = PROPOSAL_PATTERNS
    APPROVAL_PATTERNS = APPROVAL_PATTERNS
    REJECTION_PATTERNS = REJECTION_PATTERNS

    def __init__(self, llm_provider=None):
        self.llm = llm_provider

    async def analyze_simulation(self, simulation_state: SimulationState) -> SimulationMetrics:
        """Analyze a completed simulation and extract all metrics."""
        logger.info(f"Analyzing simulation: {simulation_state.config.id}")

        # Gather all messages from all rounds
        all_messages: list[SimulationMessage] = []
        for round_state in simulation_state.rounds:
            all_messages.extend(round_state.messages)

        agents = simulation_state.agents
        rounds = simulation_state.rounds

        # Compute all metrics in parallel — these are independent of each other.
        (
            compliance_rate,
            time_to_consensus,
            sentiment_trajectory,
            polarization,
            adoption_rate,
            coalitions,
            turning_points,
            activity_scores,
            decision_outcomes,
        ) = await asyncio.gather(
            self.compute_compliance_violations(all_messages, agents),
            self.compute_time_to_consensus(rounds),
            self.compute_sentiment_trajectory(rounds),
            self.compute_polarization_index(agents, all_messages),
            self.compute_policy_adoption_rate(rounds),
            self.detect_coalitions(all_messages, agents),
            self.identify_turning_points(rounds),
            self.compute_agent_activity_scores(all_messages, agents),
            self.extract_decision_outcomes(rounds),
        )

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

        logger.info(f"Analysis complete for simulation: {simulation_state.config.id}")
        return metrics

    async def compute_compliance_violations(self, messages: list[SimulationMessage], agents: list[AgentState]) -> float:
        """Detect messages/actions that violate stated policies.

        Uses LLM-based semantic detection when a provider is available
        (batched into a single call); falls back to keyword heuristics.

        Returns percentage of potentially non-compliant messages (0-100).
        """
        if not messages:
            return 0.0

        # Build agent policy map from archetype info
        agent_policies: dict[str, list[str]] = {}
        for agent in agents:
            policies = self._extract_policies_from_prompt(agent.persona_prompt)
            if policies:
                agent_policies[agent.id] = policies

        if not agent_policies:
            return 0.0

        # --- LLM path: single batched call ---------------------------------
        if self.llm:
            return await self._llm_compliance_violations(messages, agent_policies)

        # --- Keyword fallback ------------------------------------------------
        return self._keyword_compliance_violations(messages, agent_policies)

    async def _llm_compliance_violations(
        self,
        messages: list[SimulationMessage],
        agent_policies: dict[str, list[str]],
    ) -> float:
        """LLM-based compliance check — one batched call."""
        from app.llm.provider import LLMMessage

        # Build a compact summary: agent policies + sample messages to check.
        # Limit to agents that have policies and cap messages to keep prompt small.
        policy_block = "\n".join(f"Agent {aid}: {'; '.join(pols)}" for aid, pols in agent_policies.items())
        msg_block = "\n".join(f"[{m.agent_id}] {m.content[:200]}" for m in messages[:60])
        prompt = (
            "Below are agent policy constraints and their messages. "
            "Count how many messages CONTRADICT or VIOLATE the agent's "
            "own stated policies.\n\n"
            f"POLICIES:\n{policy_block}\n\n"
            f"MESSAGES ({len(messages)} total, sample shown):\n{msg_block}\n\n"
            'Respond with ONLY valid JSON: {"violation_count": N, '
            '"total_checked": N}'
        )
        try:
            resp = await self.llm.generate(
                messages=[
                    LLMMessage(
                        role="system",
                        content=(
                            "You detect policy violations in boardroom " "discussions. Respond with ONLY valid JSON."
                        ),
                    ),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.1,
                max_tokens=100,
            )
            raw = resp.content.strip().removeprefix("```json").removesuffix("```").strip()
            data = json.loads(raw)
            total = int(data.get("total_checked", len(messages)))
            violations = int(data.get("violation_count", 0))
            if total <= 0:
                return 0.0
            return round((violations / total) * 100, 2)
        except Exception:
            logger.debug("LLM compliance check failed, falling back to keywords")
            return self._keyword_compliance_violations(messages, agent_policies)

    def _keyword_compliance_violations(
        self,
        messages: list[SimulationMessage],
        agent_policies: dict[str, list[str]],
    ) -> float:
        """Keyword-based compliance fallback."""
        violation_count = 0
        for msg in messages:
            content = msg.content.lower()
            policies = agent_policies.get(msg.agent_id, [])
            for policy in policies:
                if self._is_contradictory(content, policy):
                    violation_count += 1
                    break
        return round((violation_count / len(messages)) * 100, 2)

    def _extract_policies_from_prompt(self, prompt: str) -> list[str]:
        """Extract stated policies/constraints from agent persona prompt."""
        policies = []

        prompt_lower = prompt.lower()
        for pattern in POLICY_EXTRACTION_PATTERNS:
            matches = re.finditer(pattern, prompt_lower, re.IGNORECASE)
            for match in matches:
                policies.append(match.group(1).strip())

        return policies

    def _is_contradictory(self, content: str, policy: str) -> bool:
        """Simple heuristic to detect if content contradicts a policy."""
        policy_words = set(policy.lower().split())
        content_words = set(content.lower().split())

        has_policy_negation = bool(policy_words & NEGATION_WORDS)

        # Extract key policy terms (excluding common words)
        key_terms = policy_words - STOP_WORDS - NEGATION_WORDS

        if not key_terms:
            return False

        # Check if key terms appear in content
        content_has_terms = bool(key_terms & content_words)

        # Simple contradiction: policy says "never X" but content mentions X
        if has_policy_negation and content_has_terms:
            content_has_negation = bool(content_words & NEGATION_WORDS)
            if not content_has_negation:
                return True

        return False

    async def compute_time_to_consensus(self, rounds: list[RoundState]) -> int | None:
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
                if any(re.search(p, content) for p in APPROVAL_PATTERNS):
                    return i + 1

        return None  # No consensus reached

    async def compute_sentiment_trajectory(self, rounds: list[RoundState]) -> list[dict]:
        """Track sentiment over time.

        Uses LLM-based semantic analysis when a provider is available;
        falls back to keyword matching otherwise.
        """
        if self.llm:
            return await self._llm_sentiment_trajectory(rounds)
        return self._keyword_sentiment_trajectory(rounds)

    async def _llm_sentiment_trajectory(self, rounds: list[RoundState]) -> list[dict]:
        """LLM-based sentiment: single batched call for all rounds.

        Instead of 1 LLM call per round (N calls), we send all round
        excerpts in one prompt and ask the model to return an array.
        Falls back to keyword analysis on failure.
        """
        from app.llm.provider import LLMMessage

        # Separate empty rounds (no LLM needed) from rounds with content.
        empty_rounds: dict[int, dict] = {}
        round_excerpts: list[tuple[int, str]] = []
        for rs in rounds:
            if not rs.messages:
                empty_rounds[rs.round_number] = {
                    "round": rs.round_number,
                    "positive": 0.0,
                    "negative": 0.0,
                    "neutral": 1.0,
                }
            else:
                excerpt = "\n".join(f"{m.agent_name}: {m.content[:200]}" for m in rs.messages)
                round_excerpts.append((rs.round_number, excerpt[:2000]))

        # If no rounds have content, return empties only.
        if not round_excerpts:
            return [empty_rounds[rs.round_number] for rs in rounds]

        # Build a single batched prompt.
        round_blocks = "\n\n".join(f"--- ROUND {rn} ---\n{exc}" for rn, exc in round_excerpts)
        prompt = (
            f"Rate the overall sentiment of EACH round below. "
            f"Respond with ONLY a JSON array, one object per round:\n"
            f'[{{"round": N, "positive": 0.0-1.0, "negative": 0.0-1.0, '
            f'"neutral": 0.0-1.0}}]\n'
            f"Values in each object must sum to 1.0.\n\n{round_blocks}"
        )

        try:
            resp = await self.llm.generate(
                messages=[
                    LLMMessage(
                        role="system",
                        content=("You analyze boardroom discussion sentiment. " "Respond with ONLY valid JSON."),
                    ),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.1,
                max_tokens=50 * len(round_excerpts) + 50,
            )
            raw = resp.content.strip().removeprefix("```json").removesuffix("```").strip()
            parsed: list[dict] = json.loads(raw)
            # Index by round number for fast lookup.
            by_round: dict[int, dict] = {}
            for entry in parsed:
                rn = int(entry.get("round", 0))
                by_round[rn] = {
                    "round": rn,
                    "positive": float(entry.get("positive", 0)),
                    "negative": float(entry.get("negative", 0)),
                    "neutral": float(entry.get("neutral", 0)),
                }
        except Exception:
            logger.debug("Batched LLM sentiment failed, falling back to keywords")
            return self._keyword_sentiment_trajectory(rounds)

        # Merge: LLM results for content rounds, empties for the rest.
        trajectory: list[dict] = []
        for rs in rounds:
            rn = rs.round_number
            if rn in empty_rounds:
                trajectory.append(empty_rounds[rn])
            elif rn in by_round:
                trajectory.append(by_round[rn])
            else:
                # LLM missed this round — keyword fallback.
                trajectory.append(self._keyword_sentiment_for_round(rs))

        return trajectory

    def _keyword_sentiment_trajectory(self, rounds: list[RoundState]) -> list[dict]:
        """Fallback keyword-based sentiment analysis."""
        return [self._keyword_sentiment_for_round(r) for r in rounds]

    def _keyword_sentiment_for_round(self, round_state: RoundState) -> dict:
        """Keyword sentiment for a single round."""
        if not round_state.messages:
            return {
                "round": round_state.round_number,
                "positive": 0.0,
                "negative": 0.0,
                "neutral": 1.0,
            }

        positive_count = 0
        negative_count = 0

        for msg in round_state.messages:
            content = msg.content.lower()
            words = set(re.findall(r"\b\w+\b", content))
            pos_matches = len(words & POSITIVE_WORDS)
            neg_matches = len(words & NEGATIVE_WORDS)
            if pos_matches > neg_matches:
                positive_count += 1
            elif neg_matches > pos_matches:
                negative_count += 1

        total = len(round_state.messages)
        return {
            "round": round_state.round_number,
            "positive": round(positive_count / total, 2),
            "negative": round(negative_count / total, 2),
            "neutral": round(
                (total - positive_count - negative_count) / total,
                2,
            ),
        }

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
                words = set(re.findall(r"\b\w+\b", content))
                pos_matches = len(words & POSITIVE_WORDS)
                neg_matches = len(words & NEGATIVE_WORDS)
                sentiment = (pos_matches - neg_matches) / max(len(words), 1)
                total_sentiment += sentiment

            role_sentiments[role] = total_sentiment / len(msgs) if msgs else 0

        # Calculate polarization as standard deviation from mean
        if len(role_sentiments) < 2:
            return {role: 0.0 for role in role_sentiments}

        sentiments = list(role_sentiments.values())
        mean_sentiment = sum(sentiments) / len(sentiments)

        # Calculate variance
        variance = sum((s - mean_sentiment) ** 2 for s in sentiments) / len(sentiments)
        std_dev = variance**0.5

        # Individual polarization scores (distance from mean, normalized)
        polarization = {}
        for role, sentiment in role_sentiments.items():
            distance = abs(sentiment - mean_sentiment)
            polarization[role] = round(min(distance / max(std_dev, 0.001), 2.0), 2)

        return polarization

    async def compute_policy_adoption_rate(self, rounds: list[RoundState]) -> float:
        """Calculate % of proposals that were adopted."""
        proposals = []
        adoptions = []

        for round_state in rounds:
            for msg in round_state.messages:
                content = msg.content

                # Detect proposals
                for pattern in PROPOSAL_PATTERNS:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        proposals.append(
                            {
                                "text": match.group(1).strip(),
                                "round": round_state.round_number,
                            }
                        )

            # Check decisions for adoption
            for decision in round_state.decisions:
                evaluation = decision.get("evaluation", {})
                if evaluation.get("outcome") in [
                    "approved",
                    "accepted",
                    "adopted",
                    "proposal_accepted",  # legacy boardroom
                ]:
                    adoptions.append(round_state.round_number)

        if not proposals:
            return 0.0

        # Count proposals that appear to have been adopted
        adopted_count = 0
        for proposal in proposals:
            for adoption_round in adoptions:
                if adoption_round >= proposal["round"]:
                    adopted_count += 1
                    break

        return round((adopted_count / len(proposals)) * 100, 2)

    async def detect_coalitions(self, messages: list[SimulationMessage], agents: list[AgentState]) -> list[dict]:
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
            # Track who aligns with whom
            alignments: dict[str, set[str]] = {}

            for msg in msgs:
                content_lower = msg.content.lower()
                agent_id = msg.agent_id

                for keyword in ALIGNMENT_KEYWORDS:
                    if keyword in content_lower:
                        # Find who they're aligning with
                        for other_agent in agents:
                            if other_agent.id != agent_id:
                                name_lower = other_agent.name.lower()
                                if name_lower in content_lower:
                                    if agent_id not in alignments:
                                        alignments[agent_id] = set()
                                    alignments[agent_id].add(other_agent.id)

            # Identify coalition groups (MIN_COALITION_SIZE+ agents)
            coalition_groups = self._find_coalition_groups(alignments)

            for group in coalition_groups:
                # Find coalition topic
                topic = self._extract_coalition_topic(msgs, group)

                coalitions.append(
                    {
                        "round": round_num,
                        "members": list(group),
                        "topic": topic,
                    }
                )

        return coalitions

    def _find_coalition_groups(self, alignments: dict[str, set[str]]) -> list[set[str]]:
        """Find groups of MIN_COALITION_SIZE+ mutually aligned agents."""
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

            if len(group) >= MIN_COALITION_SIZE:
                groups.append(group)
                processed.update(group)

        return groups

    def _extract_coalition_topic(self, messages: list[SimulationMessage], coalition_members: set[str]) -> str:
        """Extract the topic around which a coalition formed."""
        # Collect messages from coalition members
        member_msgs = [m for m in messages if m.agent_id in coalition_members]

        # Extract common keywords (excluding stop words)
        word_counts = Counter()
        for msg in member_msgs:
            words = re.findall(r"\b\w+\b", msg.content.lower())
            for word in words:
                if word not in COALITION_STOP_WORDS and len(word) > 3:
                    word_counts[word] += 1

        # Return most common topic words
        top_words = [w for w, c in word_counts.most_common(3)]
        return " ".join(top_words) if top_words else "general alignment"

    async def identify_turning_points(self, rounds: list[RoundState]) -> list[dict]:
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

            abs_pos = abs(pos_shift)
            abs_neg = abs(neg_shift)
            pos_over_base = abs_pos > TURNING_POINT_THRESHOLD
            neg_over_base = abs_neg > TURNING_POINT_THRESHOLD
            pos_over_high = abs_pos > TURNING_POINT_HIGH_THRESHOLD
            neg_over_high = abs_neg > TURNING_POINT_HIGH_THRESHOLD
            pos_over_med = abs_pos > TURNING_POINT_MEDIUM_THRESHOLD
            neg_over_med = abs_neg > TURNING_POINT_MEDIUM_THRESHOLD

            if pos_over_base or neg_over_base:
                # Determine impact level
                if pos_over_high or neg_over_high:
                    impact = "high"
                elif pos_over_med or neg_over_med:
                    impact = "medium"
                else:
                    impact = "low"

                # Generate description
                if pos_shift > 0:
                    description = f"Significant positive shift in sentiment " f"(+{round(pos_shift * 100)}%)"
                else:
                    description = f"Significant negative shift in sentiment " f"(+{round(abs(neg_shift) * 100)}%)"

                # Look for triggering event in messages
                round_state = rounds[i]
                if round_state.messages:
                    first_msg = round_state.messages[0]
                    description += f" triggered by {first_msg.agent_name}"

                turning_points.append(
                    {
                        "round": curr["round"],
                        "description": description,
                        "impact": impact,
                        "score": round(max(abs_pos, abs_neg), 2),
                    }
                )

        # Check for decision points
        for round_state in rounds:
            for decision in round_state.decisions:
                evaluation = decision.get("evaluation", {})
                decision_made = evaluation.get("decision_made")
                consensus_reached = evaluation.get("consensus_reached")
                if decision_made or consensus_reached:
                    # Check if not already recorded
                    already_recorded = any(tp["round"] == round_state.round_number for tp in turning_points)
                    if not already_recorded:
                        score = _derive_decision_turning_point_score(decision)
                        turning_points.append(
                            {
                                "round": round_state.round_number,
                                "description": "Key decision point reached",
                                "impact": "high",
                                "score": score,
                            }
                        )

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

            activity_scores[agent.id] = round((normalized_count * 0.7 + normalized_length * 0.3), 2)

        return activity_scores

    async def extract_decision_outcomes(self, rounds: list[RoundState]) -> list[dict]:
        """Extract decision outcomes from rounds."""
        outcomes = []

        for round_state in rounds:
            for decision in round_state.decisions:
                evaluation = decision.get("evaluation", {})

                decision_text = evaluation.get("decision", "Unknown decision")
                outcome = evaluation.get("outcome", "unknown")

                # Normalize outcome
                if outcome in APPROVED_OUTCOMES:
                    result = "approved"
                elif outcome in REJECTED_OUTCOMES:
                    result = "rejected"
                else:
                    result = "pending"

                outcomes.append(
                    {
                        "decision": decision_text,
                        "result": result,
                        "round": round_state.round_number,
                    }
                )

        return outcomes
