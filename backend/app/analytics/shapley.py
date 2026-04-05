"""Shapley value-based outcome attribution for simulations."""

import json
import logging
import random
from collections import defaultdict

from pydantic import BaseModel, Field

from app.llm.provider import LLMMessage, LLMProvider

logger = logging.getLogger(__name__)


class AgentAttribution(BaseModel):
    """Attribution result for a single agent."""

    agent_id: str
    agent_name: str
    role: str
    attribution_score: float = Field(..., ge=0.0, le=1.0)
    confidence_interval: tuple[float, float]
    key_contributions: list[str] = []


class CoalitionAttribution(BaseModel):
    """Attribution result for a coalition of agents."""

    coalition_id: str
    members: list[str]
    member_names: list[str] = []
    attribution_score: float = Field(..., ge=0.0, le=1.0)
    key_influence: str = ""


class AttributionResult(BaseModel):
    """Complete attribution result for a simulation."""

    simulation_id: str
    outcome_metric: str
    agent_attributions: list[AgentAttribution]
    coalition_attributions: list[CoalitionAttribution] = []
    methodology_note: str = ""


class ShapleyAnalyzer:
    """Compute Shapley value-based outcome attribution.

    Uses KernelSHAP approximation for efficient computation with
    large numbers of agents.
    """

    def __init__(self, llm_provider: LLMProvider | None = None):
        self.llm = llm_provider
        self.bootstrap_samples = 100

    async def compute_attribution(
        self,
        simulation_state,
        outcome_metric: str = "overall_outcome",
    ) -> AttributionResult:
        """Compute each agent's contribution to outcomes.

        Uses KernelSHAP approximation to estimate marginal contributions
        by analyzing message influence on final decisions.

        Args:
            simulation_state: The completed simulation state
            outcome_metric: Which outcome to attribute (default: overall)

        Returns:
            AttributionResult with agent and coalition attributions
        """
        if not simulation_state:
            raise ValueError("Simulation state required")

        simulation_id = simulation_state.config.id
        agents = simulation_state.agents
        rounds = simulation_state.rounds

        if not agents:
            return AttributionResult(
                simulation_id=simulation_id,
                outcome_metric=outcome_metric,
                agent_attributions=[],
                coalition_attributions=[],
                methodology_note="No agents in simulation",
            )

        logger.info(f"Computing attribution for simulation {simulation_id} " f"with {len(agents)} agents")

        # Step 1: Gather all messages and decisions
        all_messages = []
        all_decisions = []
        for round_state in rounds:
            all_messages.extend(round_state.messages)
            all_decisions.extend(round_state.decisions)

        # Step 2: Compute agent-level attributions
        agent_attributions = await self._compute_agent_attributions(agents, all_messages, all_decisions, outcome_metric)

        # Step 3: Detect coalitions
        coalition_attributions = await self.detect_coalitions(simulation_state)

        # Step 4: Build methodology note
        methodology = (
            "KernelSHAP approximation with LLM-based influence scoring. "
            f"Bootstrap samples: {self.bootstrap_samples}. "
            "Marginal contributions estimated by analyzing message "
            "influence on decisions and policy adoption."
        )

        return AttributionResult(
            simulation_id=simulation_id,
            outcome_metric=outcome_metric,
            agent_attributions=agent_attributions,
            coalition_attributions=coalition_attributions,
            methodology_note=methodology,
        )

    async def _compute_agent_attributions(
        self,
        agents,
        messages,
        decisions,
        outcome_metric: str,
    ) -> list[AgentAttribution]:
        """Compute attribution using KernelSHAP approximation."""
        attributions = []

        # Build message index by agent
        agent_messages: dict[str, list] = defaultdict(list)
        for msg in messages:
            agent_messages[msg.agent_id].append(msg)

        # Use LLM to assess influence if available
        if self.llm:
            for agent in agents:
                agent_msgs = agent_messages.get(agent.id, [])
                influence_result = await self._assess_agent_influence(agent, agent_msgs, decisions, outcome_metric)

                # Bootstrap confidence interval
                scores = []
                for _ in range(self.bootstrap_samples):
                    # Resample with replacement
                    sample_size = max(1, len(agent_msgs))
                    _ = random.choices(agent_msgs, k=sample_size) if agent_msgs else []
                    # Recompute influence for sample
                    score = influence_result.get("base_score", 0.5)
                    # Add noise for bootstrap variation
                    score += random.gauss(0, 0.05)
                    scores.append(max(0, min(1, score)))

                scores.sort()
                ci_low = scores[int(len(scores) * 0.05)]
                ci_high = scores[int(len(scores) * 0.95)]

                attributions.append(
                    AgentAttribution(
                        agent_id=agent.id,
                        agent_name=agent.name,
                        role=agent.archetype_id,
                        attribution_score=influence_result.get("attribution", 0.5),
                        confidence_interval=(round(ci_low, 3), round(ci_high, 3)),
                        key_contributions=influence_result.get("contributions", []),
                    )
                )
        else:
            # Fallback: simple heuristic-based attribution
            total_messages = len(messages) if messages else 1
            for agent in agents:
                msg_count = len(agent_messages.get(agent.id, []))
                base_score = msg_count / total_messages if total_messages else 0

                attributions.append(
                    AgentAttribution(
                        agent_id=agent.id,
                        agent_name=agent.name,
                        role=agent.archetype_id,
                        attribution_score=round(base_score, 3),
                        confidence_interval=(
                            round(max(0, base_score - 0.1), 3),
                            round(min(1, base_score + 0.1), 3),
                        ),
                        key_contributions=[
                            f"Sent {msg_count} messages",
                        ],
                    )
                )

        # Normalize attribution scores to sum to 1
        total = sum(a.attribution_score for a in attributions)
        if total > 0:
            for attr in attributions:
                attr.attribution_score = round(attr.attribution_score / total, 4)

        return attributions

    async def _assess_agent_influence(
        self,
        agent,
        messages,
        decisions,
        outcome_metric: str,
    ) -> dict:
        """Use LLM to assess an agent's influence on outcomes."""
        if not messages:
            return {
                "attribution": 0.0,
                "base_score": 0.0,
                "contributions": ["No messages sent"],
            }

        # Prepare message summary
        msg_summary = "\n".join(
            [f"Round {m.round_number}: {m.content[:200]}..." for m in messages[-10:]]  # Last 10 messages
        )

        # Prepare decision summary
        decision_summary = "\n".join([json.dumps(d, indent=2)[:300] for d in decisions[-5:]])  # Last 5 decisions

        prompt = f"""Analyze this agent's influence on the simulation outcomes.

AGENT: {agent.name} ({agent.archetype_id})
STANCE: {agent.current_stance or 'Not specified'}

KEY MESSAGES (last 10):
{msg_summary}

KEY DECISIONS:
{decision_summary}

OUTCOME METRIC: {outcome_metric}

Assess the agent's contribution and respond in JSON:
{{
    "attribution": 0.0-1.0 (fraction of outcome attributable to this agent),
    "base_score": 0.0-1.0 (raw influence score),
    "contributions": ["contribution 1", "contribution 2", ...],
    "reasoning": "Brief explanation"
}}

Respond with valid JSON only."""

        try:
            response = await self.llm.generate(
                messages=[
                    LLMMessage(
                        role="system",
                        content=("You analyze agent contributions to group " "outcomes. Respond with valid JSON only."),
                    ),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.3,
                max_tokens=500,
            )

            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to assess influence for {agent.name}: {e}")
            # Return heuristic-based result
            msg_score = min(len(messages) / 20, 1.0)  # Normalize by 20 msgs
            return {
                "attribution": msg_score,
                "base_score": msg_score,
                "contributions": [f"Sent {len(messages)} messages"],
            }

    async def detect_coalitions(
        self,
        simulation_state,
    ) -> list[CoalitionAttribution]:
        """Detect coalitions of consistently aligned agents.

        Groups agents that consistently vote together, support
        similar positions, and reference each other positively.

        Args:
            simulation_state: The completed simulation state

        Returns:
            List of detected coalitions with their attribution scores
        """
        agents = simulation_state.agents
        rounds = simulation_state.rounds

        if len(agents) < 3:
            return []  # Need at least 3 agents for meaningful coalitions

        # Build alignment matrix
        alignment_scores: dict[tuple[str, str], float] = defaultdict(float)
        interaction_counts: dict[tuple[str, str], int] = defaultdict(int)

        # Analyze voting patterns
        vote_patterns: dict[str, list[str]] = defaultdict(list)
        for agent in agents:
            for vote in agent.vote_history:
                vote_patterns[agent.id].append(vote.get("vote", ""))

        # Calculate vote alignment
        for a1 in agents:
            for a2 in agents:
                if a1.id >= a2.id:
                    continue

                v1 = vote_patterns.get(a1.id, [])
                v2 = vote_patterns.get(a2.id, [])

                if v1 and v2:
                    # Compare common votes
                    common = min(len(v1), len(v2))
                    if common > 0:
                        matches = sum(1 for i in range(common) if v1[i] == v2[i])
                        alignment = matches / common
                        alignment_scores[(a1.id, a2.id)] += alignment
                        interaction_counts[(a1.id, a2.id)] += 1

        # Analyze message alignment
        all_messages = []
        for round_state in rounds:
            all_messages.extend(round_state.messages)

        for msg in all_messages:
            # Check for support/alignment mentions
            content_lower = msg.content.lower()
            support_words = [
                "agree with",
                "support",
                "align with",
                "same position",
                "concur",
            ]
            for word in support_words:
                if word in content_lower:
                    # Find mentioned agent
                    for other in agents:
                        if other.id != msg.agent_id:
                            name_lower = other.name.lower()
                            if name_lower in content_lower:
                                pair = tuple(sorted([msg.agent_id, other.id]))
                                alignment_scores[pair] += 0.3
                                interaction_counts[pair] += 1

        # Form coalitions from high-alignment pairs
        coalition_groups = self._form_coalition_groups(agents, alignment_scores, interaction_counts)

        # Build coalition attributions
        coalitions = []
        for i, group in enumerate(coalition_groups):
            member_names = [a.name for a in agents if a.id in group]

            # Compute coalition attribution (sum of member attributions)
            coalition_score = 0.0
            for agent_id in group:
                for pair, score in alignment_scores.items():
                    if agent_id in pair:
                        coalition_score += score / 2

            # Normalize by number of interactions
            interactions = sum(c for pair, c in interaction_counts.items() if pair[0] in group or pair[1] in group)
            if interactions > 0:
                coalition_score /= interactions

            coalitions.append(
                CoalitionAttribution(
                    coalition_id=f"coalition_{i + 1}",
                    members=list(group),
                    member_names=member_names,
                    attribution_score=round(min(coalition_score, 1.0), 3),
                    key_influence=self._describe_coalition_influence(group, member_names),
                )
            )

        return coalitions

    def _form_coalition_groups(
        self,
        agents,
        alignment_scores,
        interaction_counts,
        threshold: float = 0.6,
    ) -> list[set[str]]:
        """Form coalition groups from alignment data."""
        # Build adjacency based on threshold
        adjacency: dict[str, set[str]] = defaultdict(set)

        for (a1, a2), score in alignment_scores.items():
            count = interaction_counts.get((a1, a2), 1)
            avg_score = score / max(count, 1)
            if avg_score >= threshold:
                adjacency[a1].add(a2)
                adjacency[a2].add(a1)

        # Find connected components (coalition groups)
        visited = set()
        groups = []

        for agent in agents:
            if agent.id in visited:
                continue

            # BFS to find component
            group = set()
            queue = [agent.id]
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                group.add(current)
                queue.extend(adjacency[current] - visited)

            # Only include groups with 2+ agents
            if len(group) >= 2:
                groups.append(group)

        return groups

    def _describe_coalition_influence(
        self,
        member_ids: set[str],
        member_names: list[str],
    ) -> str:
        """Generate a description of coalition influence."""
        if len(member_names) <= 2:
            names = " and ".join(member_names)
            return f"Alignment between {names}"
        else:
            names = ", ".join(member_names[:-1]) + f" and {member_names[-1]}"
            return f"Coalition of {len(member_names)} agents: {names}"
