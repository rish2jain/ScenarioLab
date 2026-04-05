"""Tests for CLICodexProvider."""

from unittest.mock import AsyncMock, patch

import pytest

from app.llm.cli_codex_provider import CLICodexProvider
from app.llm.provider import LLMMessage


@pytest.mark.asyncio
class TestCLICodexProviderGenerate:
    async def test_generate_does_not_forward_temperature_to_cli(self):
        """Codex CLI exec does not support temperature; provider accepts it for protocol only."""
        provider = CLICodexProvider(model="gpt-5.4")
        provider._cli = "/fake/codex"

        with patch.object(provider, "_run_cli", new_callable=AsyncMock) as run_cli:
            run_cli.return_value = "ok"
            await provider.generate(
                [LLMMessage(role="user", content="hi")],
                temperature=0.35,
            )

        run_cli.assert_called_once()
        assert run_cli.call_args.kwargs == {}
