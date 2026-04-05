"""Tests for InferenceRouter."""

import re
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.llm.inference_router import InferenceRouter
from app.simulation.models import SimulationMessage


def _extract_calibration_spans(content: str) -> tuple[str, str, str]:
    """Parse response/vote/stance quoted fields from ``build_exemplar_messages`` output."""
    m = re.search(
        r'Your response style:\n"(?P<response>[\s\S]*?)"\n\n'
        r'Your voting style:\n"(?P<vote>[\s\S]*?)"\n\n'
        r'Your stance summary:\n"(?P<stance>[\s\S]*?)"\n\n'
        r"Maintain this voice",
        content,
    )
    assert m is not None, "expected STYLE CALIBRATION body"
    return m.group("response"), m.group("vote"), m.group("stance")


def _mock_provider(name: str = "cloud") -> MagicMock:
    p = MagicMock()
    p.provider_name = name
    p.generate = AsyncMock()
    p.test_connection = AsyncMock(return_value={"status": "ok", "message": "ok", "model": "m"})
    return p


@pytest.mark.asyncio
class TestInferenceRouterCreate:
    async def test_cloud_mode_no_probe(self):
        cloud = _mock_provider()
        r = await InferenceRouter.create(cloud, None, "cloud")
        assert r.mode == "cloud"
        cloud.test_connection.assert_not_called()

    async def test_hybrid_degrades_when_local_none(self):
        cloud = _mock_provider()
        r = await InferenceRouter.create(cloud, None, "hybrid")
        assert r.mode == "cloud"
        assert r.local is None

    async def test_hybrid_keeps_local_on_success(self):
        cloud = _mock_provider()
        local = _mock_provider("local")
        r = await InferenceRouter.create(cloud, local, "hybrid", cloud_rounds=1)
        assert r.mode == "hybrid"
        assert r.local is local
        local.test_connection.assert_called_once()

    async def test_hybrid_degrades_on_unreachable_local(self):
        cloud = _mock_provider()
        local = _mock_provider("local")
        local.test_connection = AsyncMock(side_effect=ConnectionError("down"))
        r = await InferenceRouter.create(cloud, local, "hybrid")
        assert r.mode == "cloud"
        assert r.local is None

    async def test_local_raises_without_provider(self):
        cloud = _mock_provider()
        with pytest.raises(ValueError, match="local"):
            await InferenceRouter.create(cloud, None, "local")

    async def test_local_raises_on_bad_connection(self):
        cloud = _mock_provider()
        local = _mock_provider("local")
        local.test_connection = AsyncMock(side_effect=RuntimeError("fail"))
        with pytest.raises(ValueError, match="Local LLM"):
            await InferenceRouter.create(cloud, local, "local")


class TestGetProvider:
    def test_cloud_mode_always_cloud(self):
        cloud = _mock_provider()
        r = InferenceRouter(cloud, None, "cloud", cloud_rounds=1)
        assert r.get_provider(1, "response") is cloud
        assert r.get_provider(99, "report") is cloud

    def test_hybrid_routing(self):
        cloud = _mock_provider()
        local = _mock_provider("local")
        r = InferenceRouter(cloud, local, "hybrid", cloud_rounds=1)
        assert r.get_provider(1, "response") is cloud
        assert r.get_provider(2, "response") is local
        assert r.get_provider(2, "vote") is local
        assert r.get_provider(2, "stance") is local

    def test_hybrid_analytics_report_always_cloud(self):
        cloud = _mock_provider()
        local = _mock_provider("local")
        r = InferenceRouter(cloud, local, "hybrid", cloud_rounds=1)
        assert r.get_provider(99, "analytics") is cloud
        assert r.get_provider(99, "report") is cloud

    def test_hybrid_cloud_rounds_zero_all_local(self):
        cloud = _mock_provider()
        local = _mock_provider("local")
        r = InferenceRouter(cloud, local, "hybrid", cloud_rounds=0)
        assert r.get_provider(1, "response") is local

    def test_local_mode(self):
        cloud = _mock_provider()
        local = _mock_provider("local")
        r = InferenceRouter(cloud, local, "local", cloud_rounds=1)
        assert r.get_provider(1, "analytics") is local


class TestExemplars:
    def test_store_and_build_messages(self):
        cloud = _mock_provider()
        local = _mock_provider("local")
        r = InferenceRouter(cloud, local, "hybrid", cloud_rounds=1)

        msgs = [
            SimulationMessage(
                round_number=1,
                phase="discussion",
                agent_id="a1",
                agent_name="A",
                agent_role="ceo",
                content="Strategic opening stance.",
                message_type="statement",
            ),
            SimulationMessage(
                round_number=1,
                phase="vote",
                agent_id="a1",
                agent_name="A",
                agent_role="ceo",
                content="Vote: for. REASONING: Because synergy.",
                message_type="vote",
            ),
        ]
        r.store_exemplar("a1", msgs, stance_text="Bullish on the deal.")

        built = r.build_exemplar_messages("a1")
        assert len(built) == 1
        assert built[0].role == "user"
        assert "STYLE CALIBRATION" in built[0].content
        assert "Strategic opening" in built[0].content
        assert "synergy" in built[0].content.lower()
        assert "Bullish" in built[0].content

    def test_build_exemplar_heading_uses_cloud_rounds(self):
        """Exemplar copy references the last cloud round, not a hardcoded Round 1."""
        cloud = _mock_provider()
        local = _mock_provider("local")
        r = InferenceRouter(cloud, local, "hybrid", cloud_rounds=3)
        r.store_exemplar("a1", [], stance_text="Calibrated.")
        built = r.build_exemplar_messages("a1")
        assert len(built) == 1
        assert "Round 3" in built[0].content
        assert "Round 1" not in built[0].content

    def test_build_exemplar_generic_when_cloud_rounds_zero(self):
        """Preloaded MC follow-up uses cloud_rounds=0; heading stays non-numeric."""
        cloud = _mock_provider()
        local = _mock_provider("local")
        r = InferenceRouter(cloud, local, "hybrid", cloud_rounds=1)
        r.store_exemplar("a1", [], stance_text="S")
        r2 = r.with_preloaded_exemplars()
        built = r2.build_exemplar_messages("a1")
        assert "prior performance" in built[0].content
        assert "Round 0" not in built[0].content

    def test_build_empty_when_no_data(self):
        cloud = _mock_provider()
        local = _mock_provider("local")
        r = InferenceRouter(cloud, local, "hybrid", cloud_rounds=1)
        assert r.build_exemplar_messages("missing") == []

    def test_should_inject_exemplars(self):
        cloud = _mock_provider()
        local = _mock_provider("local")
        r = InferenceRouter(cloud, local, "hybrid", cloud_rounds=1)
        r.store_exemplar("a1", [], stance_text="x")
        assert r.should_inject_exemplars("a1", 2, "response") is True
        assert r.should_inject_exemplars("a1", 1, "response") is False
        assert r.should_inject_exemplars("a1", 2, "analytics") is False

    def test_with_preloaded_exemplars(self):
        cloud = _mock_provider()
        local = _mock_provider("local")
        r = InferenceRouter(cloud, local, "hybrid", cloud_rounds=1)
        long_resp = "x" * 2000
        long_stance = "y" * 500
        msgs = [
            SimulationMessage(
                round_number=1,
                phase="x",
                agent_id="a1",
                agent_name="A",
                agent_role="ceo",
                content=long_resp,
                message_type="statement",
            ),
        ]
        r.store_exemplar("a1", msgs, stance_text=long_stance)
        r2 = r.with_preloaded_exemplars()
        assert r.has_exemplars()
        assert r2.has_exemplars()
        assert r.exemplars_shared_with(r2)
        assert r2.cloud_rounds == 0
        assert r2.mode == "hybrid"
        assert r2.get_provider(1, "response") is local

        built = r.build_exemplar_messages("a1")
        built2 = r2.build_exemplar_messages("a1")
        assert len(built) == len(built2) == 1
        assert "Round 1" in built[0].content
        assert "prior performance" in built2[0].content

        resp, _, stance = _extract_calibration_spans(built[0].content)
        resp2, _, stance2 = _extract_calibration_spans(built2[0].content)
        assert resp == resp2 and stance == stance2
        assert len(resp) <= 500
        assert len(stance) <= 200


class TestExemplarSnapshotRoundTrip:
    def test_snapshot_restore_preserves_injection(self):
        cloud = _mock_provider()
        local = _mock_provider("local")
        r = InferenceRouter(cloud, local, "hybrid", cloud_rounds=1)
        msgs = [
            SimulationMessage(
                round_number=1,
                phase="x",
                agent_id="a1",
                agent_name="A",
                agent_role="ceo",
                content="cloud style",
                message_type="statement",
            ),
        ]
        r.store_exemplar("a1", msgs, stance_text="stance text")
        snap = r.snapshot_exemplars()
        r2 = InferenceRouter(cloud, local, "hybrid", cloud_rounds=1)
        assert not r2.has_exemplars()
        r2.restore_exemplars(snap)
        assert r2.should_inject_exemplars("a1", 2, "response") is True
        assert "stance text" in (r2.build_exemplar_messages("a1")[0].content)


class TestExemplarTruncation:
    def test_truncation(self):
        cloud = _mock_provider()
        local = _mock_provider("local")
        r = InferenceRouter(cloud, local, "hybrid", cloud_rounds=1)
        long_resp = "x" * 2000
        msgs = [
            SimulationMessage(
                round_number=1,
                phase="x",
                agent_id="a1",
                agent_name="A",
                agent_role="ceo",
                content=long_resp,
                message_type="statement",
            ),
        ]
        r.store_exemplar("a1", msgs, stance_text="y" * 500)
        built = r.build_exemplar_messages("a1")
        resp, _, stance = _extract_calibration_spans(built[0].content)
        assert len(resp) <= 500
        assert len(stance) <= 200
