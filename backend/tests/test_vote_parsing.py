"""Tests for vote parsing and response sanitization."""

from app.simulation.agent import parse_vote_from_response, sanitize_llm_response


class TestSanitizeLlmResponse:
    def test_strips_think_tags(self):
        raw = "<think>internal reasoning</think>The actual response."
        assert sanitize_llm_response(raw) == "internal reasoningThe actual response."

    def test_strips_closing_think_tag_only(self):
        raw = "Some leaked reasoning</think>\nThe real answer."
        assert "</think>" not in sanitize_llm_response(raw)

    def test_detects_chinese_hallucination(self):
        raw = "壳牌石油公司的投资战略需要重新审视市场定位"
        result = sanitize_llm_response(raw)
        assert result.startswith("[HALLUCINATION_DETECTED")

    def test_mixed_english_chinese_below_threshold(self):
        raw = "The CEO proposed expanding into 中国 markets for growth."
        result = sanitize_llm_response(raw)
        assert not result.startswith("[HALLUCINATION_DETECTED")

    def test_empty_string(self):
        assert sanitize_llm_response("") == ""

    def test_none_like(self):
        assert sanitize_llm_response(None) == ""

    def test_pure_english_unchanged(self):
        raw = "I support the proposal with minor reservations."
        assert sanitize_llm_response(raw) == raw


class TestParseVoteFromResponse:
    def test_explicit_vote_line_wins(self):
        assert (
            parse_vote_from_response("VOTE: against\nREASONING: too risky")
            == "against"
        )

    def test_vote_line_case_insensitive(self):
        assert parse_vote_from_response("vote: FOR\nreasoning: ok") == "for"

    def test_abstain_explicit(self):
        assert parse_vote_from_response("VOTE: abstain\nREASONING: unclear") == (
            "abstain"
        )

    def test_no_false_positive_information(self):
        """'for' must not match inside unrelated words via word boundaries."""
        assert (
            parse_vote_from_response(
                "REASONING: See information and data before deciding.\n"
                "VOTE: abstain"
            )
            == "abstain"
        )

    def test_word_boundary_for(self):
        assert parse_vote_from_response("I am for this plan.") == "for"

    def test_chinese_body_abstain_without_vote_line(self):
        """Without structured VOTE line, non-English body defaults to abstain."""
        assert parse_vote_from_response("我弃权。") == "abstain"

    # --- New edge cases ---

    def test_against_not_overridden_by_for_in_reasoning(self):
        """'I oppose this for good reasons' should be against, not for."""
        text = "I oppose this proposal for several important reasons."
        assert parse_vote_from_response(text) == "against"

    def test_against_in_complex_sentence(self):
        text = (
            "The proposal is still not board-ready for capital release. "
            "I vote against further authorization."
        )
        assert parse_vote_from_response(text) == "against"

    def test_support_keyword(self):
        text = "I support the revised tranche proposal."
        assert parse_vote_from_response(text) == "for"

    def test_approve_keyword(self):
        text = "I approve the motion as amended."
        assert parse_vote_from_response(text) == "for"

    def test_voting_for_phrase(self):
        text = "I am voting for this initiative."
        assert parse_vote_from_response(text) == "for"

    def test_bare_for_without_voting_context_abstains(self):
        """Bare 'for' without voting verbs should not match as a vote."""
        text = "This is for the benefit of all stakeholders."
        assert parse_vote_from_response(text) == "abstain"

    def test_hallucinated_response_abstains(self):
        text = "壳牌石油公司的投资战略需要重新审视市场定位和竞争优势"
        assert parse_vote_from_response(text) == "abstain"

    def test_think_tags_stripped_before_parsing(self):
        text = "<think>reasoning</think>VOTE: against\nREASONING: bad plan"
        assert parse_vote_from_response(text) == "against"

    def test_empty_input(self):
        assert parse_vote_from_response("") == "abstain"
        assert parse_vote_from_response(None) == "abstain"
