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
                [
                    LLMMessage(role="system", content="sys body"),
                    LLMMessage(role="assistant", content="asst body"),
                    LLMMessage(role="user", content="hi"),
                    LLMMessage(role="", content="empty-role body"),
                    LLMMessage(role="   ", content="whitespace-role body"),
                ],
                temperature=0.35,
            )

        run_cli.assert_called_once()
        assert run_cli.call_args.kwargs == {}
        prompt = run_cli.call_args.args[0]
        assert "[System]" in prompt
        assert "sys body" in prompt
        assert "[Previous response]" in prompt
        assert "asst body" in prompt
        assert "[User]" in prompt
        assert "hi" in prompt
        assert "[unknown]" in prompt
        assert "empty-role body" in prompt
        assert "whitespace-role body" in prompt
