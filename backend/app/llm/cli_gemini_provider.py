"""Gemini CLI LLM provider."""

import asyncio
import logging
import shutil
from typing import AsyncIterator

from app.config import settings
from app.llm.provider import (
    MAX_TOKENS_CAP,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    get_llm_semaphore,
    terminate_process_with_timeout,
)

logger = logging.getLogger(__name__)


class CLIGeminiProvider(LLMProvider):
    """Provider that shells out to the Gemini CLI."""

    provider_name = "cli-gemini"

    def __init__(self, model: str = ""):
        if model and not model.lower().startswith("gemini"):
            logger.warning(
                "Invalid model '%s' for Gemini CLI (must start with 'gemini'). " "Using the CLI default model instead.",
                model,
            )
            model = ""
        self.model = model
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
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=settings.gemini_cli_timeout)
        except asyncio.TimeoutError:
            await terminate_process_with_timeout(proc)
            raise RuntimeError(f"Gemini CLI timed out after {settings.gemini_cli_timeout}s")

        if proc.returncode != 0:
            err = stderr.decode().strip()
            raise RuntimeError(f"Gemini CLI exited with code " f"{proc.returncode}: {err}")

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
        async with get_llm_semaphore(self.provider_name):
            # Gemini CLI takes a single prompt; combine messages
            parts = []
            for msg in messages:
                if msg.role == "system":
                    parts.append(f"[System]\n{msg.content}")
                elif msg.role == "user":
                    parts.append(msg.content)
                elif msg.role == "assistant":
                    parts.append(f"[Previous response]\n{msg.content}")

            prompt = "\n\n".join(parts)
            content = await self._run_cli(prompt, max_tokens=max_tokens)

            return LLMResponse(
                content=content,
                model=self.model or "provider default",
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
        response = await self.generate(messages, temperature, max_tokens, **kwargs)
        yield response.content

    async def test_connection(self) -> dict:
        """Test that the Gemini CLI is available.

        The version check subprocess is capped at ``settings.gemini_cli_version_check_timeout``
        seconds to mirror the timeout and cleanup behaviour of ``_run_cli``.
        """
        if not self._cli:
            return {
                "status": "error",
                "message": "Gemini CLI not found in PATH",
                "model": self.model or "provider default",
            }
        proc: asyncio.subprocess.Process | None = None
        try:
            proc = await asyncio.create_subprocess_exec(
                self._cli,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(
                proc.communicate(),
                timeout=settings.gemini_cli_version_check_timeout,
            )
            version = stdout.decode().strip()
            return {
                "status": "ok",
                "message": f"Gemini CLI available: {version}",
                "model": self.model or "provider default",
            }
        except asyncio.TimeoutError:
            if proc is not None:
                await terminate_process_with_timeout(proc)
            return {
                "status": "error",
                "message": (
                    f"Gemini CLI version check timed out " f"after {settings.gemini_cli_version_check_timeout}s"
                ),
                "model": self.model or "provider default",
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "model": self.model or "provider default",
            }
