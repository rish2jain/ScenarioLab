"""llama.cpp LLM provider."""

import logging
from typing import AsyncIterator

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.llm.provider import (
    LLMMessage,
    LLMProvider,
    LLMResponse,
    get_llm_semaphore,
)

logger = logging.getLogger(__name__)

DEFAULT_LLAMACPP_URL = "http://localhost:8080/v1"


class LlamaCppProvider(LLMProvider):
    """llama.cpp provider using HTTP server (OpenAI-compatible mode)."""

    provider_name = "llamacpp"

    def __init__(self, model: str, base_url: str = DEFAULT_LLAMACPP_URL):
        """Initialize the llama.cpp provider.

        Args:
            model: Model name
            base_url: llama.cpp HTTP server base URL
        """
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=300.0,  # Long timeout for local inference
        )
        logger.info(f"Initialized llama.cpp provider with model: {model} at {base_url}")

    def _convert_messages(self, messages: list[LLMMessage]) -> list[dict]:
        """Convert LLMMessage objects to OpenAI format."""
        return [{"role": msg.role, "content": msg.content} for msg in messages]

    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> LLMResponse:
        """Generate a completion from messages."""
        async with get_llm_semaphore(self.provider_name):
            return await self._generate_with_retry(messages, temperature, max_tokens, **kwargs)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ConnectTimeout)),
        before_sleep=lambda retry_state: logger.warning(
            f"llama.cpp call failed, retrying (attempt "
            f"{retry_state.attempt_number}): "
            f"{retry_state.outcome.exception()}"
        ),
    )
    async def _generate_with_retry(
        self,
        messages: list[LLMMessage],
        temperature: float,
        max_tokens: int,
        **kwargs,
    ) -> LLMResponse:
        """Generate a completion with retry logic."""
        try:
            llama_messages = self._convert_messages(messages)
            request_body = {
                "model": self.model,
                "messages": llama_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs,
            }

            response = await self.client.post(
                "/chat/completions",
                json=request_body,
            )
            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"] or ""
            usage = data.get("usage")

            return LLMResponse(
                content=content,
                model=data.get("model", self.model),
                provider=self.provider_name,
                usage=usage,
            )
        except (httpx.ConnectError, httpx.ConnectTimeout):
            raise
        except Exception as e:
            logger.error(f"Error generating completion: {e}")
            raise

    async def stream(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream a completion token by token."""
        try:
            llama_messages = self._convert_messages(messages)
            request_body = {
                "model": self.model,
                "messages": llama_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
                **kwargs,
            }

            async with self.client.stream(
                "POST",
                "/chat/completions",
                json=request_body,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[6:]  # Remove "data: " prefix
                    if data == "[DONE]":
                        break
                    try:
                        import json

                        chunk = json.loads(data)
                        if chunk.get("choices") and chunk["choices"][0].get("delta", {}).get("content"):
                            yield chunk["choices"][0]["delta"]["content"]
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Error streaming completion: {e}")
            raise

    async def test_connection(self) -> dict:
        """Test connectivity to the llama.cpp server."""
        try:
            # Try a minimal chat completion with a short timeout so
            # capability probes don't block for 5 minutes.
            request_body = {
                "model": self.model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5,
            }

            response = await self.client.post(
                "/chat/completions",
                json=request_body,
                timeout=5.0,
            )
            response.raise_for_status()
            data = response.json()

            return {
                "status": "ok",
                "message": "Connection successful",
                "model": data.get("model", self.model),
            }
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "model": self.model,
            }
