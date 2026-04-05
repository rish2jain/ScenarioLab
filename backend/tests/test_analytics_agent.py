"""Tests for analytics heuristic helpers in AnalyticsAgent.

These tests cover the pure-Python parsing and analysis methods that do
NOT require a live LLM — they can run fully offline.
"""

import re

import pytest

from app.analytics.analytics_agent import (
    AnalyticsAgent,
    _decision_meta_for_score,
    _derive_decision_turning_point_score,
)
from app.analytics.prompts import (
    APPROVAL_PATTERNS,
    MIN_COALITION_SIZE,
    NEGATIVE_WORDS,
    POSITIVE_WORDS,
    PROPOSAL_PATTERNS,
    TURNING_POINT_HIGH_THRESHOLD,
    TURNING_POINT_MEDIUM_THRESHOLD,
    TURNING_POINT_THRESHOLD,
)
from app.simulation.models import RoundState, SimulationMessage

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def agent():
    """Return an AnalyticsAgent with no LLM provider (offline tests only)."""
    return AnalyticsAgent(llm_provider=None)


def _make_msg(agent_id: str, content: str):
    """Build a minimal message mock with agent_id and content."""
    from unittest.mock import MagicMock

    m = MagicMock()
    m.agent_id = agent_id
    m.content = content
    return m


# ---------------------------------------------------------------------------
# prompts.py constants sanity
# ---------------------------------------------------------------------------


class TestPromptsConstants:
    def test_positive_words_non_empty(self):
        assert len(POSITIVE_WORDS) > 0

    def test_negative_words_non_empty(self):
        assert len(NEGATIVE_WORDS) > 0

    def test_sets_are_disjoint(self):
        """No word should simultaneously be positive and negative."""
        overlap = POSITIVE_WORDS & NEGATIVE_WORDS
        assert not overlap, f"Overlap between POSITIVE/NEGATIVE_WORDS: {overlap}"

    def test_proposal_patterns_are_valid_regex(self):
        for pattern in PROPOSAL_PATTERNS:
            re.compile(pattern)  # must not raise

    def test_approval_patterns_are_valid_regex(self):
        for pattern in APPROVAL_PATTERNS:
            re.compile(pattern)  # must not raise


# ---------------------------------------------------------------------------
# _extract_policies_from_prompt
# ---------------------------------------------------------------------------


class TestExtractPoliciesFromPrompt:
    def test_extracts_must_policy(self, agent):
        prompt = "You must maintain data confidentiality at all times."
        policies = agent._extract_policies_from_prompt(prompt)
        assert len(policies) >= 1
        assert any("confidentiality" in p for p in policies)

    def test_extracts_goal(self, agent):
        prompt = "Your goal is to maximize shareholder returns and reduce costs."
        policies = agent._extract_policies_from_prompt(prompt)
        assert any("shareholder" in p or "returns" in p for p in policies)

    def test_empty_prompt_returns_empty_list(self, agent):
        assert agent._extract_policies_from_prompt("") == []

    def test_no_policy_keywords_returns_empty(self, agent):
        prompt = "The sun is shining brightly today."
        # Generic text with no policy indicators — must yield an empty list
        policies = agent._extract_policies_from_prompt(prompt)
        assert policies == [], f"Expected no policies for generic prompt, got: {policies}"

    def test_multiple_policies_extracted(self, agent):
        prompt = (
            "You must protect employee welfare. "
            "Always ensure regulatory compliance. "
            "Never compromise client data."
        )
        policies = agent._extract_policies_from_prompt(prompt)
        assert len(policies) >= 2


# ---------------------------------------------------------------------------
# _is_contradictory
# ---------------------------------------------------------------------------


class TestIsContradictory:
    def test_never_policy_contradiction(self, agent):
        """Content mentioning X when policy says 'never X' → True."""
        policy = "never share confidential information"
        content = "i will share all confidential information with the press"
        assert agent._is_contradictory(content, policy) is True

    def test_never_policy_no_contradiction(self, agent):
        """Content that also negates X when policy says 'never X' → False."""
        policy = "never share confidential information"
        content = "we will not share confidential information"
        assert agent._is_contradictory(content, policy) is False

    def test_no_negation_in_policy_no_contradiction(self, agent):
        """Policy without a negation word never triggers contradiction."""
        policy = "maintain transparency with all stakeholders"
        content = "we refuse to maintain any transparency"
        assert agent._is_contradictory(content, policy) is False

    def test_empty_policy_returns_false(self, agent):
        assert agent._is_contradictory("some content", "") is False

    def test_empty_content_returns_false(self, agent):
        policy = "never expose trade secrets"
        assert agent._is_contradictory("", policy) is False


# ---------------------------------------------------------------------------
# _find_coalition_groups
# ---------------------------------------------------------------------------


class TestFindCoalitionGroups:
    def test_three_mutual_agents_form_coalition(self, agent):
        alignments = {
            "a1": {"a2", "a3"},
            "a2": {"a1", "a3"},
            "a3": {"a1", "a2"},
        }
        groups = agent._find_coalition_groups(alignments)
        assert len(groups) == 1
        assert {"a1", "a2", "a3"}.issubset(groups[0])

    @pytest.mark.skipif(
        MIN_COALITION_SIZE <= 2,
        reason="test requires MIN_COALITION_SIZE > 2",
    )
    def test_two_agents_below_min_threshold(self, agent):
        # Pair size is 2; expect [] when below MIN_COALITION_SIZE
        alignments = {
            "a1": {"a2"},
            "a2": {"a1"},
        }
        groups = agent._find_coalition_groups(alignments)
        assert groups == []

    def test_empty_alignments_returns_empty(self, agent):
        assert agent._find_coalition_groups({}) == []

    def test_single_agent_no_coalition(self, agent):
        alignments = {"a1": set()}
        groups = agent._find_coalition_groups(alignments)
        assert groups == []


# ---------------------------------------------------------------------------
# _extract_coalition_topic
# ---------------------------------------------------------------------------


class TestExtractCoalitionTopic:
    def test_most_common_word_is_returned(self, agent):
        """The most frequent non-stop word across member messages appears in topic."""
        messages = [
            _make_msg("a1", "We support the merger proposal completely"),
            _make_msg("a2", "This merger is an excellent opportunity"),
            _make_msg("a3", "The merger plan seems very promising"),
        ]
        topic = agent._extract_coalition_topic(messages, {"a1", "a2", "a3"})
        assert "merger" in topic

    def test_empty_messages_returns_default(self, agent):
        topic = agent._extract_coalition_topic([], {"a1"})
        assert topic == "general alignment"

    def test_non_member_messages_excluded(self, agent):
        messages = [
            _make_msg("a1", "This proposal is great"),  # member
            _make_msg("outsider", "unicorn rainbow butterfly sunshine"),  # non-member
        ]
        topic = agent._extract_coalition_topic(messages, {"a1"})
        assert "unicorn" not in topic


# ---------------------------------------------------------------------------
# identify_turning_points (threshold-based impact / score)
# ---------------------------------------------------------------------------


def _sentiment_round(
    round_number: int,
    total_messages: int,
    n_positive: int,
    n_negative: int,
) -> RoundState:
    """Build a round whose sentiment rates are n_pos/total and n_neg/total."""
    n_neutral = total_messages - n_positive - n_negative
    assert n_neutral >= 0
    msgs: list[SimulationMessage] = []
    for _ in range(n_positive):
        msgs.append(
            SimulationMessage(
                round_number=round_number,
                phase="main",
                agent_id="a1",
                agent_name="Alpha",
                agent_role="tester",
                content="good excellent success",
            )
        )
    for _ in range(n_negative):
        msgs.append(
            SimulationMessage(
                round_number=round_number,
                phase="main",
                agent_id="a1",
                agent_name="Alpha",
                agent_role="tester",
                content="bad worst problem",
            )
        )
    for _ in range(n_neutral):
        msgs.append(
            SimulationMessage(
                round_number=round_number,
                phase="main",
                agent_id="a1",
                agent_name="Alpha",
                agent_role="tester",
                content="hello there",
            )
        )
    return RoundState(
        round_number=round_number,
        phase="main",
        messages=msgs,
        decisions=[],
    )


@pytest.mark.asyncio
class TestIdentifyTurningPoints:
    """Synthetic two-round series to exercise ``identify_turning_points`` tiers."""

    async def test_no_turning_point_when_shift_at_or_below_base_threshold(self, agent):
        """|Δsentiment| <= TURNING_POINT_THRESHOLD → no sentiment turning point."""
        # 0.39 - 0.10 = 0.29 (strict base check is `> TURNING_POINT_THRESHOLD`)
        r1 = _sentiment_round(1, 100, 10, 0)
        r2 = _sentiment_round(2, 100, 39, 0)
        out = await agent.identify_turning_points([r1, r2])
        assert out == []

    async def test_low_impact_when_score_between_base_and_medium(self, agent):
        """Base satisfied, but max shift <= MEDIUM threshold → impact low."""
        assert TURNING_POINT_THRESHOLD < 0.36 < TURNING_POINT_MEDIUM_THRESHOLD
        r1 = _sentiment_round(1, 50, 15, 0)
        r2 = _sentiment_round(2, 50, 33, 0)
        out = await agent.identify_turning_points([r1, r2])
        assert len(out) == 1
        tp = out[0]
        assert tp["round"] == 2
        assert tp["impact"] == "low"
        assert tp["score"] == pytest.approx(0.36, abs=1e-9)
        assert set(tp) >= {"round", "description", "impact", "score"}

    async def test_medium_impact_when_score_between_medium_and_high(self, agent):
        assert TURNING_POINT_MEDIUM_THRESHOLD < 0.42 < TURNING_POINT_HIGH_THRESHOLD
        r1 = _sentiment_round(1, 50, 15, 0)
        r2 = _sentiment_round(2, 50, 36, 0)
        out = await agent.identify_turning_points([r1, r2])
        assert len(out) == 1
        tp = out[0]
        assert tp["impact"] == "medium"
        assert tp["score"] == pytest.approx(0.42, abs=1e-9)

    async def test_high_impact_when_score_above_high_threshold(self, agent):
        assert TURNING_POINT_HIGH_THRESHOLD < 0.56
        r1 = _sentiment_round(1, 50, 10, 0)
        r2 = _sentiment_round(2, 50, 38, 0)
        out = await agent.identify_turning_points([r1, r2])
        assert len(out) == 1
        tp = out[0]
        assert tp["impact"] == "high"
        assert tp["score"] == pytest.approx(0.56, abs=1e-9)

    async def test_edge_shift_equals_base_threshold_not_a_turning_point(self, agent):
        """Exactly T: `abs > T` is false → no event."""
        r1 = _sentiment_round(1, 50, 15, 0)
        r2 = _sentiment_round(2, 50, 30, 0)
        out = await agent.identify_turning_points([r1, r2])
        assert out == []

    async def test_edge_shift_equals_medium_threshold_classified_low(self, agent):
        """Exactly M: `abs > M` is false → still low (not medium)."""
        r1 = _sentiment_round(1, 50, 15, 0)
        r2 = _sentiment_round(2, 50, 35, 0)
        out = await agent.identify_turning_points([r1, r2])
        assert len(out) == 1
        assert out[0]["impact"] == "low"
        assert out[0]["score"] == pytest.approx(0.4, abs=1e-9)

    async def test_edge_shift_equals_high_threshold_classified_medium(self, agent):
        """Exactly H: `abs > H` is false → medium, not high."""
        r1 = _sentiment_round(1, 50, 10, 0)
        r2 = _sentiment_round(2, 50, 35, 0)
        out = await agent.identify_turning_points([r1, r2])
        assert len(out) == 1
        assert out[0]["impact"] == "medium"
        assert out[0]["score"] == pytest.approx(0.5, abs=1e-9)


# ---------------------------------------------------------------------------
# _decision_meta_for_score
# ---------------------------------------------------------------------------


class TestDecisionMetaForScore:
    def test_truthy_non_dict_evaluation_does_not_raise(self):
        meta = _decision_meta_for_score({"evaluation": "not a dict", "importance": 0.5})
        assert meta["importance"] == 0.5

    def test_dict_evaluation_merged(self):
        meta = _decision_meta_for_score({"evaluation": {"importance": 0.2}, "foo": "bar"})
        assert meta["importance"] == 0.2
        assert meta["foo"] == "bar"


# ---------------------------------------------------------------------------
# _derive_decision_turning_point_score
# ---------------------------------------------------------------------------


class TestDeriveDecisionTurningPointScore:
    def test_vote_result_uses_largest_bloc_ratio(self):
        assert _derive_decision_turning_point_score(
            {
                "evaluation": {
                    "vote_result": {
                        "result": "passed",
                        "for": 3,
                        "against": 2,
                        "abstain": 0,
                        "total": 5,
                    },
                },
            }
        ) == pytest.approx(0.6, abs=1e-9)

    def test_consensus_reached_only_when_no_richer_metadata(self):
        assert _derive_decision_turning_point_score(
            {
                "evaluation": {"consensus_reached": True},
            }
        ) == pytest.approx(0.85, abs=1e-9)

    def test_decision_made_only(self):
        assert _derive_decision_turning_point_score(
            {
                "evaluation": {"decision_made": True},
            }
        ) == pytest.approx(0.75, abs=1e-9)

    def test_agreement_reached_takes_precedence_over_decision_made(self):
        assert _derive_decision_turning_point_score(
            {
                "evaluation": {"agreement_reached": True, "decision_made": True},
            }
        ) == pytest.approx(0.9, abs=1e-9)

    def test_consensus_count_over_total(self):
        assert _derive_decision_turning_point_score(
            {
                "evaluation": {
                    "consensus_count": 4,
                    "total_votes": 5,
                },
            }
        ) == pytest.approx(0.8, abs=1e-9)

    def test_importance_normalized(self):
        assert _derive_decision_turning_point_score(
            {
                "evaluation": {"importance": 8},
            }
        ) == pytest.approx(0.8, abs=1e-9)

    def test_empty_meta_fallback(self):
        assert _derive_decision_turning_point_score({}) == 1.0
