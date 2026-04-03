"""Gemini CLI LLM provider."""

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

# Maximum seconds to wait for the Gemini CLI subprocess to respond.
GEMINI_CLI_TIMEOUT: float = 120.0


class CLIGeminiProvider(LLMProvider):
    """Provider that shells out to the Gemini CLI."""

    provider_name = "cli-gemini"

    def __init__(self, model: str = ""):
        self.model = model or "gemini-3.1-pro"
        self._cli = shutil.which("gemini")
        if not self._cli:
            logger.warning(
                "Gemini CLI not found in PATH. "
                "See https://ai.google.dev/gemini-api/docs/cli "
                "for installation instructions."
            )

    async def _run_cli(
        self,
        prompt: str,
        max_tokens: int = 2048,
    ) -> str:
        """Run the Gemini CLI and return stdout."""
        cmd = [self._cli or "gemini"]

        if self.model:
            cmd.extend(["--model", self.model])

        cmd.extend(["--prompt", prompt])

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=GEMINI_CLI_TIMEOUT
            )
        except asyncio.TimeoutError:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
            raise RuntimeError(
                f"Gemini CLI timed out after {GEMINI_CLI_TIMEOUT}s"
            )

        if proc.returncode != 0:
            err = stderr.decode().strip()
            raise RuntimeError(
                f"Gemini CLI exited with code "
                f"{proc.returncode}: {err}"
            )

        return stdout.decode().strip()

    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> LLMResponse:
        """Generate a completion via the Gemini CLI.

        Note: The Gemini CLI does not expose a ``--temperature`` flag.
        The *temperature* parameter is accepted for interface compatibility
        but is silently ignored.  Use the Gemini API provider directly if
        you need to control sampling temperature.
        """
        if temperature != 0.7:
            logger.warning(
                "CLIGeminiProvider does not support the 'temperature' "
                "parameter (the Gemini CLI has no --temperature flag). "
                "The provided value %.2f will be ignored.",
                temperature,
            )
        max_tokens = min(max_tokens, MAX_TOKENS_CAP)
        async with _llm_semaphore:
            # Gemini CLI takes a single prompt; combine messages
            parts = []
            for msg in messages:
                if msg.role == "system":
                    parts.append(f"[System]\n{msg.content}")
                elif msg.role == "user":
                    parts.append(msg.content)
                elif msg.role == "assistant":
                    parts.append(
                        f"[Previous response]\n{msg.content}"
                    )

            prompt = "\n\n".join(parts)
            content = await self._run_cli(
                prompt, max_tokens=max_tokens
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
        """Stream not supported by CLI; falls back to generate."""
        response = await self.generate(
            messages, temperature, max_tokens, **kwargs
        )
        yield response.content

    async def test_connection(self) -> dict:
        """Test that the Gemini CLI is available."""
        if not self._cli:
            return {
                "status": "error",
                "message": "Gemini CLI not found in PATH",
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
                "message": f"Gemini CLI available: {version}",
                "model": self.model,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "model": self.model,
            }
