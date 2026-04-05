"""Claude CLI LLM provider."""

import asyncio
import logging
import shutil
from typing import AsyncIterator

from app.config import settings
from app.llm.provider import (
    LLMMessage,
    LLMProvider,
    LLMResponse,
    get_llm_semaphore,
    terminate_process_with_timeout,
)

logger = logging.getLogger(__name__)


class CLIClaudeProvider(LLMProvider):
    """Provider that shells out to the Claude CLI."""

    provider_name = "cli-claude"

    def __init__(self, model: str = ""):
        # Ignore non-Claude model names (e.g. "gpt-4" from a shared config)
        if model and not model.lower().startswith("claude"):
            logger.warning(
                "Ignoring non-Claude model name %r for cli-claude; " "using the CLI default model instead.",
                model,
            )
            model = ""
        self.model = model
        self._cli = shutil.which("claude")
        if not self._cli:
            logger.warning(
                "Claude CLI not found in PATH. "
                "Install using Anthropic's native installers: "
                "https://docs.anthropic.com/en/claude-code/installation — "
                "macOS/Linux: 'curl -fsSL https://claude.ai/install.sh | sh', "
                "or Windows: see the link above. "
                "(Legacy: npm install -g @anthropic-ai/claude-code)"
            )

    async def _run_cli(
        self,
        prompt: str,
        system: str = "",
    ) -> str:
        """Run the Claude CLI and return stdout."""
        cmd = [
            self._cli or "claude",
            "--print",
            "--output-format",
            "text",
        ]
        if self.model:
            cmd.extend(["--model", self.model])
        if system:
            cmd.extend(["--system-prompt", system])

        # Pass prompt via stdin to avoid OS argument length limits
        # on long simulation prompts.
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=prompt.encode()),
                timeout=settings.claude_cli_timeout,
            )
        except asyncio.TimeoutError:
            await terminate_process_with_timeout(proc)
            raise RuntimeError(f"Claude CLI timed out after {settings.claude_cli_timeout}s")

        if proc.returncode != 0:
            err = stderr.decode().strip() or stdout.decode().strip()
            raise RuntimeError(f"Claude CLI exited with code {proc.returncode}: {err}")

        return stdout.decode().strip()

    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> LLMResponse:
        """Generate a completion via the Claude CLI."""
        # max_tokens is part of LLMProvider; Claude CLI has no token-limit flag wired here.
        async with get_llm_semaphore(self.provider_name):
            system_parts = []
            user_parts = []

            for msg in messages:
                if msg.role == "system":
                    system_parts.append(msg.content)
                else:
                    user_parts.append(f"[{msg.role}]: {msg.content}")

            # System text uses --system-prompt; the user prompt uses role prefixes on
            # each non-system turn so multi-turn [user]/[assistant] context is visible
            # to the CLI as a single transcript.
            system = "\n\n".join(system_parts)
            prompt = "\n\n".join(user_parts)

            content = await self._run_cli(prompt, system=system)

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
        """Test that the Claude CLI is available."""
        if not self._cli:
            return {
                "status": "error",
                "message": "Claude CLI not found in PATH",
                "model": self.model or "provider default",
            }
        try:
            proc = await asyncio.create_subprocess_exec(
                self._cli,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, _ = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=settings.claude_cli_version_check_timeout,
                )
            except asyncio.TimeoutError:
                await terminate_process_with_timeout(proc)
                return {
                    "status": "error",
                    "message": (
                        f"Claude CLI version check timed out after " f"{settings.claude_cli_version_check_timeout}s"
                    ),
                    "model": self.model or "provider default",
                }
            version = stdout.decode().strip()
            return {
                "status": "ok",
                "message": f"Claude CLI available: {version}",
                "model": self.model or "provider default",
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "model": self.model or "provider default",
            }
