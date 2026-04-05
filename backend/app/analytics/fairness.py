"""Bias and fairness auditing for simulation outcomes."""

import json
import logging
import random
from collections import defaultdict

from pydantic import BaseModel, Field

from app.llm.provider import LLMMessage, LLMProvider

logger = logging.getLogger(__name__)


class FairnessMetric(BaseModel):
    """A single fairness metric comparing two groups."""

    dimension: str
    group_a: str
    group_b: str
    metric_value: float
    p_value: float | None = None
    significant: bool = False


class FairnessReport(BaseModel):
    """Complete fairness audit report for a simulation."""

    simulation_id: str
    perturbation_type: str
    metrics: list[FairnessMetric]
    overall_fairness_score: float = Field(..., ge=0.0, le=1.0)
    recommendations: list[str] = []
    methodology_note: str = ""


# Gender name mappings for perturbation analysis
GENDER_NAME_MAPPINGS: dict[str, dict[str, str]] = {
    "male_to_female": {
        "James": "Jane",
        "John": "Joan",
        "Robert": "Roberta",
        "Michael": "Michelle",
        "William": "Willow",
        "David": "Diana",
        "Richard": "Rachel",
        "Joseph": "Josephine",
        "Thomas": "Thomasina",
        "Charles": "Charlotte",
        "Christopher": "Christina",
        "Daniel": "Danielle",
        "Matthew": "Matilda",
        "Anthony": "Antonia",
        "Mark": "Marcia",
        "Steven": "Stephanie",
        "Paul": "Paula",
        "Andrew": "Andrea",
        "Joshua": "Joshlyn",
        "Kenneth": "Kendra",
        "Kevin": "Keva",
        "Brian": "Brianna",
        "George": "Georgia",
        "Edward": "Edwina",
        "Ronald": "Rhonda",
        "Timothy": "Tiffany",
        "Jason": "Jasmine",
        "Jeffrey": "Jennifer",
        "Ryan": "Ryanne",
        "Jacob": "Jacqueline",
        "Gary": "Grace",
        "Nicholas": "Nicole",
        "Eric": "Erica",
        "Jonathan": "Joni",
        "Stephen": "Stephanie",
        "Larry": "Laura",
        "Justin": "Justine",
        "Scott": "Scottie",
        "Brandon": "Brenda",
        "Raymond": "Raye",
        "Samuel": "Samantha",
        "Benjamin": "Benjamina",
        "Gregory": "Gregoria",
        "Frank": "Frances",
        "Alexander": "Alexandra",
        "Patrick": "Patricia",
        "Jack": "Jackie",
        "Dennis": "Denise",
        "Jerry": "Geraldine",
        "Tyler": "Tyler",
        "Aaron": "Erin",
        "Jose": "Josefina",
        "Adam": "Ada",
        "Henry": "Henrietta",
        "Nathan": "Natalie",
        "Douglas": "Douglas",
        "Zachary": "Zacharya",
        "Peter": "Petra",
        "Kyle": "Kylie",
        "Ethan": "Ethel",
        "Walter": "Wanda",
        "Noah": "Noelle",
        "Jeremy": "Jeremiah",
        "Christian": "Christine",
        "Keith": "Keira",
        "Roger": "Rogene",
    },
    "female_to_male": {},
}

# Build reverse mapping
for male, female in GENDER_NAME_MAPPINGS["male_to_female"].items():
    GENDER_NAME_MAPPINGS["female_to_male"][female] = male


class FairnessAuditor:
    """Audit simulations for bias and fairness issues.

    Uses perturbation analysis (e.g., gender-flipping agent names)
    to detect demographic bias in agent behavior patterns.
    """

    # Perturbation types and their descriptions
    PERTURBATION_TYPES = {
        "gender": "Gender-flip agent names and compare behavior",
        "name_length": "Compare agents with short vs long names",
        "random": "Random group assignment as control",
    }

    def __init__(self, llm_provider: LLMProvider | None = None):
        self.llm = llm_provider

    async def audit_simulation(
        self,
        simulation_state,
        perturbation_type: str = "gender",
    ) -> FairnessReport:
        """Audit a simulation for fairness issues.

        Args:
            simulation_state: The completed simulation state
            perturbation_type: Type of perturbation analysis
                (gender, name_length, random)

        Returns:
            FairnessReport with metrics and recommendations
        """
        if not simulation_state:
            raise ValueError("Simulation state required")

        simulation_id = simulation_state.config.id
        agents = simulation_state.agents
        rounds = simulation_state.rounds

        if len(agents) < 2:
            return FairnessReport(
                simulation_id=simulation_id,
                perturbation_type=perturbation_type,
                metrics=[],
                overall_fairness_score=1.0,
                recommendations=["Insufficient agents for fairness analysis"],
                methodology_note="Need at least 2 agents for comparison",
            )

        logger.info(f"Auditing simulation {simulation_id} for {perturbation_type} bias")

        # Gather all messages
        all_messages = []
        for round_state in rounds:
            all_messages.extend(round_state.messages)

        # Step 1: Partition agents into groups
        groups = self._partition_agents(agents, perturbation_type)

        if len(groups) < 2:
            return FairnessReport(
                simulation_id=simulation_id,
                perturbation_type=perturbation_type,
                metrics=[],
                overall_fairness_score=1.0,
                recommendations=[
                    f"Could not partition agents for {perturbation_type}",
                ],
                methodology_note="Need at least 2 groups for comparison",
            )

        # Step 2: Compute metrics for each group
        metrics = await self._compute_group_metrics(agents, all_messages, groups, perturbation_type)

        # Step 3: Compute overall fairness score
        overall_score = self._compute_overall_fairness(metrics)

        # Step 4: Generate recommendations
        recommendations = self._generate_recommendations(metrics, overall_score)

        methodology = (
            f"Perturbation analysis with {perturbation_type} grouping. "
            "Metrics computed: message rate, sentiment positivity, "
            "decision influence. P-values via permutation test."
        )

        return FairnessReport(
            simulation_id=simulation_id,
            perturbation_type=perturbation_type,
            metrics=metrics,
            overall_fairness_score=overall_score,
            recommendations=recommendations,
            methodology_note=methodology,
        )

    def _partition_agents(
        self,
        agents,
        perturbation_type: str,
    ) -> dict[str, list[str]]:
        """Partition agents into groups for comparison."""
        groups: dict[str, list[str]] = defaultdict(list)

        if perturbation_type == "gender":
            # Group by gendered name patterns
            male_names = set(GENDER_NAME_MAPPINGS["male_to_female"].keys())
            female_names = set(GENDER_NAME_MAPPINGS["female_to_male"].keys())

            for agent in agents:
                parts = (agent.name or "").strip().split()
                if not parts:
                    groups["unknown_gender"].append(agent.id)
                    continue
                name = parts[0]
                if name in male_names:
                    groups["male_names"].append(agent.id)
                elif name in female_names:
                    groups["female_names"].append(agent.id)
                else:
                    groups["unknown_gender"].append(agent.id)

        elif perturbation_type == "name_length":
            # Group by name length
            name_lengths = [(a.id, len(a.name)) for a in agents]
            if name_lengths:
                lengths = [length for _, length in name_lengths]
                median = sorted(lengths)[len(lengths) // 2]
                for agent_id, length in name_lengths:
                    if length <= median:
                        groups["short_names"].append(agent_id)
                    else:
                        groups["long_names"].append(agent_id)

        elif perturbation_type == "random":
            # Random assignment as control
            shuffled = [a.id for a in agents]
            random.shuffle(shuffled)
            mid = len(shuffled) // 2
            groups["group_a"] = shuffled[:mid]
            groups["group_b"] = shuffled[mid:]

        else:
            # Default: role-based grouping
            for agent in agents:
                groups[agent.archetype_id].append(agent.id)

        return dict(groups)

    async def _compute_group_metrics(
        self,
        agents,
        messages,
        groups: dict[str, list[str]],
        perturbation_type: str,
    ) -> list[FairnessMetric]:
        """Compute fairness metrics comparing groups."""
        metrics = []

        # Get group names
        group_names = list(groups.keys())
        if len(group_names) < 2:
            return metrics

        # Metric 1: Message rate disparity
        group_message_counts = defaultdict(int)
        for msg in messages:
            for group_name, agent_ids in groups.items():
                if msg.agent_id in agent_ids:
                    group_message_counts[group_name] += 1

        # Normalize by group size
        group_msg_rates = {}
        for group_name, agent_ids in groups.items():
            group_size = len(agent_ids)
            if group_size > 0:
                group_msg_rates[group_name] = group_message_counts[group_name] / group_size

        if len(group_msg_rates) >= 2:
            rates = list(group_msg_rates.values())
            disparity = abs(rates[0] - rates[1]) / max(max(rates), 0.001)
            p_val = self._permutation_test(messages, groups, "message_count")

            metrics.append(
                FairnessMetric(
                    dimension="message_rate",
                    group_a=group_names[0],
                    group_b=group_names[1],
                    metric_value=round(disparity, 4),
                    p_value=round(p_val, 4),
                    significant=p_val < 0.05,
                )
            )

        # Metric 2: Sentiment disparity
        group_sentiments = await self._compute_group_sentiments(messages, groups)

        if len(group_sentiments) >= 2:
            sentiments = list(group_sentiments.values())
            disparity = abs(sentiments[0] - sentiments[1])
            p_val = self._permutation_test(messages, groups, "sentiment")

            metrics.append(
                FairnessMetric(
                    dimension="sentiment_positivity",
                    group_a=group_names[0],
                    group_b=group_names[1],
                    metric_value=round(disparity, 4),
                    p_value=round(p_val, 4),
                    significant=p_val < 0.05,
                )
            )

        # Metric 3: Decision influence (if LLM available)
        if self.llm:
            influence_disparity = await self._compute_influence_disparity(agents, messages, groups)

            if influence_disparity is not None:
                metrics.append(
                    FairnessMetric(
                        dimension="decision_influence",
                        group_a=group_names[0],
                        group_b=group_names[1],
                        metric_value=round(influence_disparity, 4),
                        p_value=None,
                        significant=influence_disparity > 0.2,
                    )
                )

        return metrics

    async def _compute_group_sentiments(
        self,
        messages,
        groups: dict[str, list[str]],
    ) -> dict[str, float]:
        """Compute average sentiment for each group."""
        positive_words = {
            "agree",
            "support",
            "approve",
            "positive",
            "good",
            "excellent",
            "benefit",
            "advantage",
            "success",
        }
        negative_words = {
            "disagree",
            "oppose",
            "reject",
            "negative",
            "bad",
            "poor",
            "problem",
            "issue",
            "concern",
            "risk",
        }

        group_sentiments: dict[str, list[float]] = defaultdict(list)

        for msg in messages:
            for group_name, agent_ids in groups.items():
                if msg.agent_id in agent_ids:
                    content = msg.content.lower()
                    words = set(content.split())
                    pos = len(words & positive_words)
                    neg = len(words & negative_words)
                    total = pos + neg
                    if total > 0:
                        sentiment = pos / total
                        group_sentiments[group_name].append(sentiment)

        # Average sentiments per group
        avg_sentiments = {}
        for group_name, sentiments in group_sentiments.items():
            if sentiments:
                avg_sentiments[group_name] = sum(sentiments) / len(sentiments)
            else:
                avg_sentiments[group_name] = 0.5

        return avg_sentiments

    def _permutation_test(
        self,
        messages,
        groups: dict[str, list[str]],
        metric_type: str,
        n_permutations: int = 1000,
    ) -> float:
        """Run permutation test for statistical significance."""
        group_names = list(groups.keys())
        if len(group_names) < 2:
            return 1.0

        # Compute observed difference
        observed = self._compute_statistic(messages, groups, metric_type)

        # Permutation test
        all_agent_ids = []
        for agent_ids in groups.values():
            all_agent_ids.extend(agent_ids)

        if len(all_agent_ids) < 2:
            return 1.0

        more_extreme = 0
        group_sizes = [len(groups[g]) for g in group_names]

        for _ in range(n_permutations):
            # Shuffle agent IDs
            shuffled = all_agent_ids.copy()
            random.shuffle(shuffled)

            # Create new groups
            perm_groups = {}
            idx = 0
            for i, gname in enumerate(group_names):
                perm_groups[gname] = shuffled[idx : idx + group_sizes[i]]
                idx += group_sizes[i]

            # Compute statistic for permuted groups
            perm_stat = self._compute_statistic(messages, perm_groups, metric_type)

            if abs(perm_stat) >= abs(observed):
                more_extreme += 1

        return (more_extreme + 1) / (n_permutations + 1)

    def _compute_statistic(
        self,
        messages,
        groups: dict[str, list[str]],
        metric_type: str,
    ) -> float:
        """Compute test statistic for permutation test."""
        group_names = list(groups.keys())
        if len(group_names) < 2:
            return 0.0

        if metric_type == "message_count":
            counts = []
            for gname in group_names[:2]:
                count = sum(1 for m in messages if m.agent_id in groups[gname])
                size = len(groups[gname])
                counts.append(count / max(size, 1))

            return abs(counts[0] - counts[1])

        elif metric_type == "sentiment":
            # Reuse sentiment computation
            sentiments = {}
            positive_words = {"agree", "support", "good", "positive"}
            negative_words = {"disagree", "oppose", "bad", "negative"}

            for gname in group_names[:2]:
                scores = []
                for msg in messages:
                    if msg.agent_id in groups[gname]:
                        content = msg.content.lower()
                        pos = sum(1 for w in positive_words if w in content)
                        neg = sum(1 for w in negative_words if w in content)
                        if pos + neg > 0:
                            scores.append(pos / (pos + neg))
                sentiments[gname] = sum(scores) / len(scores) if scores else 0.5

            return abs(sentiments[group_names[0]] - sentiments[group_names[1]])

        return 0.0

    async def _compute_influence_disparity(
        self,
        agents,
        messages,
        groups: dict[str, list[str]],
    ) -> float | None:
        """Use LLM to assess influence disparity between groups."""
        if not self.llm:
            return None

        group_names = list(groups.keys())
        if len(group_names) < 2:
            return None

        # Get sample messages from each group
        group_msgs = defaultdict(list)
        for msg in messages:
            for gname, agent_ids in groups.items():
                if msg.agent_id in agent_ids:
                    group_msgs[gname].append(msg.content[:200])

        samples = {gname: msgs[:5] for gname, msgs in group_msgs.items()}  # First 5 messages per group

        prompt = f"""Compare the influence of two agent groups in a simulation.

GROUP A ({group_names[0]}): {len(groups[group_names[0]])} agents
Sample messages:
{json.dumps(samples.get(group_names[0], [])[:3], indent=2)}

GROUP B ({group_names[1]}): {len(groups[group_names[1]])} agents
Sample messages:
{json.dumps(samples.get(group_names[1], [])[:3], indent=2)}

Rate the influence disparity between groups (0 = equal, 1 = maximum disparity).
Respond with JSON:
{{"disparity": 0.0-1.0, "reasoning": "brief explanation"}}"""

        try:
            response = await self.llm.generate(
                messages=[
                    LLMMessage(
                        role="system",
                        content=("You analyze group dynamics for fairness. " "Respond with valid JSON only."),
                    ),
                    LLMMessage(role="user", content=prompt),
                ],
                temperature=0.3,
                max_tokens=200,
            )

            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            result = json.loads(content)
            return result.get("disparity", 0.0)
        except Exception as e:
            logger.error(f"Failed to compute influence disparity: {e}")
            return None

    def _compute_overall_fairness(
        self,
        metrics: list[FairnessMetric],
    ) -> float:
        """Compute overall fairness score from metrics."""
        if not metrics:
            return 1.0

        # Weighted average of metric values (inverted)
        total_weight = 0.0
        weighted_sum = 0.0

        for metric in metrics:
            # Lower metric value = more fair
            # Invert so higher score = more fair
            fairness = 1.0 - metric.metric_value
            weight = 1.0

            # Significant metrics get higher weight
            if metric.significant:
                weight = 2.0
                # If significant, penalize fairness
                fairness *= 0.8

            weighted_sum += fairness * weight
            total_weight += weight

        return round(weighted_sum / total_weight, 4) if total_weight else 1.0

    def _generate_recommendations(
        self,
        metrics: list[FairnessMetric],
        overall_score: float,
    ) -> list[str]:
        """Generate recommendations based on metrics."""
        recommendations = []

        for metric in metrics:
            if metric.significant:
                recommendations.append(
                    f"Significant {metric.dimension} disparity detected "
                    f"between {metric.group_a} and {metric.group_b} "
                    f"(p={metric.p_value:.4f})"
                )
            elif metric.metric_value > 0.2:
                recommendations.append(
                    f"Moderate {metric.dimension} disparity observed " f"between {metric.group_a} and {metric.group_b}"
                )

        if overall_score >= 0.9:
            recommendations.append("Overall simulation shows good fairness characteristics")
        elif overall_score >= 0.7:
            recommendations.append("Consider reviewing agent behavior for potential bias")
        else:
            recommendations.append("Significant fairness concerns detected - " "recommend detailed review")

        return recommendations

    def generate_fairness_report(
        self,
        audit_results: FairnessReport,
    ) -> dict:
        """Generate a visualizable fairness report.

        Args:
            audit_results: The audit results to format

        Returns:
            Dictionary with visualizable data
        """
        return {
            "summary": {
                "simulation_id": audit_results.simulation_id,
                "perturbation_type": audit_results.perturbation_type,
                "overall_fairness_score": audit_results.overall_fairness_score,
                "metrics_count": len(audit_results.metrics),
                "significant_issues": sum(1 for m in audit_results.metrics if m.significant),
            },
            "metrics": [
                {
                    "dimension": m.dimension,
                    "groups": [m.group_a, m.group_b],
                    "value": m.metric_value,
                    "p_value": m.p_value,
                    "significant": m.significant,
                }
                for m in audit_results.metrics
            ],
            "recommendations": audit_results.recommendations,
            "visualizations": {
                "fairness_gauge": {
                    "value": audit_results.overall_fairness_score,
                    "ranges": [
                        {"min": 0.0, "max": 0.6, "label": "Poor", "color": "red"},
                        {"min": 0.6, "max": 0.8, "label": "Fair", "color": "yellow"},
                        {"min": 0.8, "max": 1.0, "label": "Good", "color": "green"},
                    ],
                },
                "metrics_bar_chart": [
                    {
                        "label": m.dimension,
                        "value": m.metric_value,
                        "threshold": 0.2,
                    }
                    for m in audit_results.metrics
                ],
            },
            "methodology": audit_results.methodology_note,
        }
