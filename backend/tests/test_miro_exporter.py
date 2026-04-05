"""Tests for MiroBoardExporter with mocked httpx calls.

Covers: successful board creation, API auth failure (401), rate limit (429),
network timeout, and empty report guard.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.reports.exporters.miro import MiroBoardExporter, MiroExportResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def exporter():
    return MiroBoardExporter(api_token="test-token-abc")


@pytest.fixture
def mock_async_client():
    """AsyncMock configured as an async context manager (httpx.AsyncClient shape)."""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


def _make_report(empty: bool = False):
    """Build a minimal SimulationReport mock."""
    report = MagicMock()
    report.simulation_name = "Test Simulation"
    if empty:
        report.executive_summary = None
        report.risk_register = None
        report.scenario_matrix = None
        report.stakeholder_heatmap = None
    else:
        summary = MagicMock()
        summary.summary_text = "Summary text for testing purposes. " * 5
        summary.key_findings = ["Finding 1", "Finding 2"]
        summary.recommendations = []
        report.executive_summary = summary
        report.risk_register = None
        report.scenario_matrix = None
        report.stakeholder_heatmap = None
    return report


def _ok_response(data: dict) -> MagicMock:
    """Return a mock httpx Response with status 200."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()  # no-op
    return resp


def _error_response(status_code: int) -> MagicMock:
    """Return a mock httpx Response that raises HTTPStatusError."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        message=f"HTTP {status_code}",
        request=MagicMock(),
        response=resp,
    )
    return resp


# ---------------------------------------------------------------------------
# _create_board
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCreateBoard:

    async def test_returns_board_id_on_success(self, exporter, mock_async_client):
        mock_resp = _ok_response({"id": "board-xyz"})
        mock_async_client.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value = mock_async_client

            board_id = await exporter._create_board("Test Board")
            assert board_id == "board-xyz"

    async def test_raises_on_401_unauthorized(self, exporter, mock_async_client):
        mock_resp = _error_response(401)
        mock_async_client.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value = mock_async_client

            with pytest.raises(httpx.HTTPStatusError):
                await exporter._create_board("Test Board")

    async def test_raises_on_429_rate_limit(self, exporter, mock_async_client):
        mock_resp = _error_response(429)
        mock_async_client.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value = mock_async_client

            with pytest.raises(httpx.HTTPStatusError):
                await exporter._create_board("Test Board")

    async def test_raises_on_network_timeout(self, exporter, mock_async_client):
        mock_async_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value = mock_async_client

            with pytest.raises(httpx.TimeoutException):
                await exporter._create_board("Test Board")


# ---------------------------------------------------------------------------
# export_report (integration-level with mocked HTTP)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestExportReport:

    def _mock_post_factory(self, call_count_tracker: list):
        """Returns an async callable that yields unique frame/item IDs per call."""
        counter = {"n": 0}

        async def _post(*args, **kwargs):
            counter["n"] += 1
            call_count_tracker.append(counter["n"])
            resp = MagicMock(spec=httpx.Response)
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {"id": f"item-{counter['n']}"}
            return resp

        return _post

    async def test_export_returns_miroexportresult(self, exporter, mock_async_client):
        mock_post = self._mock_post_factory([])
        mock_async_client.post = mock_post

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value = mock_async_client

            report = _make_report()
            result = await exporter.export_report(report)

        assert isinstance(result, MiroExportResult)
        assert result.board_id.startswith("item-")
        # _make_report: five layout frames (board is a separate POST); exec summary → 3 stickies
        assert result.frames_created == 5
        assert result.sticky_notes_created == 3
        assert result.cards_created == 0
        assert result.connectors_created == 0

    async def test_export_empty_report_still_returns_result(self, exporter, mock_async_client):
        """A report with no sections must still produce a valid result
        without raising."""
        calls = []
        mock_post = self._mock_post_factory(calls)
        mock_async_client.post = mock_post

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client_cls.return_value = mock_async_client

            report = _make_report(empty=True)
            result = await exporter.export_report(report)

        assert isinstance(result, MiroExportResult)
        assert result.sticky_notes_created == 0
        assert result.cards_created == 0


# ---------------------------------------------------------------------------
# export_report_mock (no HTTP calls — unit test the mock path)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestExportReportMock:

    async def test_mock_export_returns_dict_with_mock_mode(self, exporter):
        report = _make_report()
        result = await exporter.export_report_mock(report)

        assert isinstance(result, dict)
        assert result.get("mock_mode") is True

    async def test_mock_export_includes_board_name(self, exporter):
        report = _make_report()
        result = await exporter.export_report_mock(report)
        assert "Test Simulation" in result["board_name"]

    async def test_mock_export_with_executive_summary(self, exporter):
        report = _make_report()
        result = await exporter.export_report_mock(report)
        frames = result.get("frames", [])
        summary_frame = next((f for f in frames if f["title"] == "Executive Summary"), None)
        assert summary_frame is not None
        assert len(summary_frame["items"]) >= 1

    async def test_mock_export_creates_frames(self, exporter):
        report = _make_report()
        result = await exporter.export_report_mock(report)
        assert result["stats"]["frames_created"] >= 1
