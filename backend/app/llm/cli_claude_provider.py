"""Claude CLI LLM provider."""

import asyncio
import logging
import shutil
from typing import AsyncIterator

from app.llm.provider import (
    MAX_TOKENS_CAP,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    _llm_semaphore,
)

logger = logging.getLogger(__name__)


class CLIClaudeProvider(LLMProvider):
    """Provider that shells out to the Claude CLI."""

    provider_name = "cli-claude"

    def __init__(self, model: str = ""):
        self.model = model or "claude-sonnet-4-6"
        self._cli = shutil.which("claude")
        if not self._cli:
            logger.warning(
                "Claude CLI not found in PATH. "
                "Install via: npm install -g @anthropic-ai/claude-code"
            )

    async def _run_cli(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 2048,
    ) -> str:
        """Run the Claude CLI and return stdout."""
        cmd = [
            self._cli or "claude",
            "--print",
            "--output-format", "text",
        ]
        if self.model:
            cmd.extend(["--model", self.model])
        if max_tokens:
            cmd.extend(["--max-tokens", str(max_tokens)])
        if system:
            cmd.extend(["--system-prompt", system])

        cmd.extend(["--", prompt])

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            err = stderr.decode().strip()
            raise RuntimeError(
                f"Claude CLI exited with code {proc.returncode}: {err}"
            )

        return stdout.decode().strip()

    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> LLMResponse:
        """Generate a completion via the Claude CLI."""
        max_tokens = min(max_tokens, MAX_TOKENS_CAP)
        async with _llm_semaphore:
            system_parts = []
            user_parts = []

            for msg in messages:
                if msg.role == "system":
                    system_parts.append(msg.content)
                else:
                    user_parts.append(msg.content)

            system = "\n\n".join(system_parts)
            prompt = "\n\n".join(user_parts)

            content = await self._run_cli(
                prompt, system=system, max_tokens=max_tokens
            )

            return LLMResponse(
                content=content,
                model=self.model,
                provider=self.provider_name,
                usage=None,
            )

    async def stream(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream is not supported by CLI; falls back to generate."""
        response = await self.generate(
            messages, temperature, max_tokens, **kwargs
        )
        yield response.content

    async def test_connection(self) -> dict:
        """Test that the Claude CLI is available."""
        if not self._cli:
            return {
                "status": "error",
                "message": "Claude CLI not found in PATH",
                "model": self.model,
            }
        try:
            proc = await asyncio.create_subprocess_exec(
                self._cli, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            version = stdout.decode().strip()
            return {
                "status": "ok",
                "message": f"Claude CLI available: {version}",
                "model": self.model,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "model": self.model,
            }
