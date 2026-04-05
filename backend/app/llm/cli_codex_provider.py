"""Codex CLI LLM provider."""

import asyncio
import logging
import os
import shutil
import tempfile
from typing import AsyncIterator

from app.llm.provider import (
    LLMMessage,
    LLMProvider,
    LLMResponse,
    get_llm_semaphore,
)

logger = logging.getLogger(__name__)

CODEX_CLI_TIMEOUT: float = 180.0


class CLICodexProvider(LLMProvider):
    """Provider that shells out to the Codex CLI."""

    provider_name = "cli-codex"
    _VERSION_CHECK_TIMEOUT: float = 10.0

    def __init__(self, model: str = ""):
        self.model = model.strip()
        self._cli = shutil.which("codex")
        if not self._cli:
            logger.warning("Codex CLI not found in PATH. Install the Codex CLI to use " "the cli-codex provider.")

    async def _run_cli(self, prompt: str) -> str:
        """Run the Codex CLI and return the final message text.

        Sampling (temperature, etc.) is not configurable via ``codex exec``; the CLI
        uses its default/API behavior. ``generate()`` still accepts ``temperature``
        and ``max_tokens`` for the shared ``LLMProvider`` protocol but does not
        forward them here—``codex exec`` exposes no matching flags.
        """
        cli = self._cli or "codex"

        with tempfile.NamedTemporaryFile(
            mode="w+",
            encoding="utf-8",
            suffix=".txt",
            delete=False,
        ) as output_file:
            output_path = output_file.name

        try:
            cmd = [
                cli,
                "exec",
                "--color",
                "never",
                "--sandbox",
                "read-only",
                "--skip-git-repo-check",
                "--ephemeral",
                "-o",
                output_path,
            ]
            if self.model:
                cmd.extend(["-m", self.model])
            cmd.append("-")

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=prompt.encode("utf-8")),
                    timeout=CODEX_CLI_TIMEOUT,
                )
            except asyncio.TimeoutError:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                raise RuntimeError(f"Codex CLI timed out after {CODEX_CLI_TIMEOUT}s")

            if proc.returncode != 0:
                err = (
                    stderr.decode("utf-8", errors="replace").strip() or stdout.decode("utf-8", errors="replace").strip()
                )
                raise RuntimeError(f"Codex CLI exited with code {proc.returncode}: {err}")

            with open(output_path, encoding="utf-8") as result_file:
                content = result_file.read().strip()

            if not content:
                content = stdout.decode("utf-8", errors="replace").strip()
            return content
        finally:
            try:
                os.unlink(output_path)
            except OSError:
                pass

    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> LLMResponse:
        """Generate a completion via the Codex CLI.

        Output comes from ``_run_cli(prompt)`` (see that method); the flattened
        ``prompt`` is built from ``messages``. ``temperature`` and ``max_tokens``
        are accepted on ``generate`` for the shared ``LLMProvider`` protocol but
        are no-ops for this provider: the Codex CLI does not support them for
        ``exec``, so they are ignored and do not affect the result.
        """
        async with get_llm_semaphore(self.provider_name):
            parts = [
                "You are being used as a text-only reasoning engine inside a "
                "simulation backend. Reply with content only. Do not describe "
                "tool usage, do not run shell commands, and do not modify files."
            ]
            for msg in messages:
                if msg.role == "system":
                    parts.append(f"[System]\n{msg.content}")
                elif msg.role == "assistant":
                    parts.append(f"[Previous response]\n{msg.content}")
                else:
                    parts.append(msg.content)

            prompt = "\n\n".join(parts)
            content = await self._run_cli(prompt)

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
        """Stream is not supported by CLI; falls back to generate."""
        response = await self.generate(messages, temperature, max_tokens, **kwargs)
        yield response.content

    async def test_connection(self) -> dict:
        """Test that the Codex CLI is available."""
        if not self._cli:
            return {
                "status": "error",
                "message": "Codex CLI not found in PATH",
                "model": self.model or "provider default",
            }

        proc = await asyncio.create_subprocess_exec(
            self._cli,
            "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self._VERSION_CHECK_TIMEOUT,
            )
            version = (
                stdout.decode("utf-8", errors="replace").strip() or stderr.decode("utf-8", errors="replace").strip()
            )
            return {
                "status": "ok",
                "message": f"Codex CLI available: {version}",
                "model": self.model or "provider default",
            }
        except asyncio.TimeoutError:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
            return {
                "status": "error",
                "message": (f"Codex CLI version check timed out after " f"{self._VERSION_CHECK_TIMEOUT}s"),
                "model": self.model or "provider default",
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "model": self.model or "provider default",
            }
