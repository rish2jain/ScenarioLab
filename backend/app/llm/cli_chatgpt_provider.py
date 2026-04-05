"""ChatGPT CLI (OpenAI CLI) LLM provider."""

import asyncio
import json
import logging
import shutil
from typing import AsyncIterator

from app.llm.provider import (
    MAX_TOKENS_CAP,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    get_llm_semaphore,
)

logger = logging.getLogger(__name__)

# Maximum seconds to wait for the CLI subprocess to produce a response.
CHATGPT_CLI_TIMEOUT: float = 120.0


class CLIChatGPTProvider(LLMProvider):
    """Provider that shells out to the OpenAI/ChatGPT CLI."""

    provider_name = "cli-chatgpt"
    # Timeout for the CLI version check subprocess (seconds).
    _VERSION_CHECK_TIMEOUT: float = 10.0

    def __init__(self, model: str = ""):
        if model and not (model.startswith("gpt") or model.startswith("o")):
            logger.warning(
                "Unsupported model '%s' provided; using CLI default model instead.",
                model,
            )
            model = ""
        self.model = model
        # Try both 'chatgpt' and 'openai' CLI names
        self._cli = shutil.which("chatgpt") or shutil.which("openai")
        if not self._cli:
            logger.warning(
                "ChatGPT/OpenAI CLI not found in PATH. "
                "Install via: pip install openai "
                "(provides the 'openai' CLI)"
            )

    async def _run_cli(
        self,
        prompt: str,
        model: str = "",
        max_tokens: int = 2048,
    ) -> str:
        """Run the OpenAI CLI and return stdout.

        Uses `openai api chat.completions.create` subcommand.
        """
        cli = self._cli or "openai"
        cmd = [
            cli,
            "api",
            "chat.completions.create",
            "--message",
            "user",
            prompt,
            "--max-tokens",
            str(max_tokens),
        ]
        resolved_model = model or self.model
        if resolved_model:
            # Insert "-m" and resolved_model into cmd immediately before "--message" (CLI model flag).
            cmd.insert(3, "-m")
            cmd.insert(4, resolved_model)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=CHATGPT_CLI_TIMEOUT)
        except asyncio.TimeoutError:
            # Kill the stalled process and reap it before re-raising.
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
            raise RuntimeError(f"ChatGPT CLI timed out after {CHATGPT_CLI_TIMEOUT}s")

        if proc.returncode != 0:
            err = stderr.decode().strip()
            raise RuntimeError(f"ChatGPT CLI exited with code " f"{proc.returncode}: {err}")

        raw = stdout.decode().strip()

        # The openai CLI returns JSON; extract the content
        try:
            data = json.loads(raw)
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", raw)
        except json.JSONDecodeError:
            pass

        return raw

    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> LLMResponse:
        """Generate a completion via the ChatGPT/OpenAI CLI."""
        max_tokens = min(max_tokens, MAX_TOKENS_CAP)
        async with get_llm_semaphore(self.provider_name):
            # Build a combined prompt from messages
            # The openai CLI supports -g role content pairs
            # but for simplicity we combine into one prompt
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
        """Test that the ChatGPT/OpenAI CLI is available.

        The version check subprocess is capped at ``_VERSION_CHECK_TIMEOUT``
        seconds to mirror the timeout and cleanup behaviour of ``_run_cli``.
        """
        if not self._cli:
            return {
                "status": "error",
                "message": "ChatGPT/OpenAI CLI not found in PATH",
                "model": self.model or "provider default",
            }
        proc = await asyncio.create_subprocess_exec(
            self._cli,
            "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=self._VERSION_CHECK_TIMEOUT)
            version = stdout.decode().strip()
            return {
                "status": "ok",
                "message": f"ChatGPT/OpenAI CLI available: {version}",
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
                "message": (f"ChatGPT/OpenAI CLI version check timed out " f"after {self._VERSION_CHECK_TIMEOUT}s"),
                "model": self.model or "provider default",
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "model": self.model or "provider default",
            }
