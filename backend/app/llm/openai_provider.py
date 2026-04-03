"""OpenAI-compatible LLM provider."""

import logging
from typing import AsyncIterator

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, RateLimitError
from openai.types.chat import ChatCompletion
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.llm.provider import (
    MAX_TOKENS_CAP,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    _llm_semaphore,
)

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI-compatible provider for OpenAI, Qwen, etc."""  # noqa: E501

    provider_name = "openai"

    def __init__(self, api_key: str, base_url: str, model: str):
        """Initialize the OpenAI provider.

        Args:
            api_key: API key for authentication
            base_url: Base URL for the API endpoint
            model: Model name to use
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        logger.info(f"Initialized OpenAI provider with model: {model}")

    def _convert_messages(self, messages: list[LLMMessage]) -> list[dict]:
        """Convert LLMMessage objects to OpenAI format."""
        return [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> LLMResponse:
        """Generate a completion from messages."""
        max_tokens = min(max_tokens, MAX_TOKENS_CAP)
        async with _llm_semaphore:
            return await self._generate_with_retry(
                messages, temperature, max_tokens, **kwargs
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(
            (RateLimitError, APITimeoutError, APIConnectionError)
        ),
        before_sleep=lambda retry_state: logger.warning(
            f"LLM call failed, retrying (attempt "
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
            openai_messages = self._convert_messages(messages)
            response: ChatCompletion = (
                await self.client.chat.completions.create(
                    model=self.model,
                    messages=openai_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
            )

            content = response.choices[0].message.content or ""
            usage = None
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return LLMResponse(
                content=content,
                model=response.model or self.model,
                provider=self.provider_name,
                usage=usage,
            )
        except (RateLimitError, APITimeoutError, APIConnectionError):
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
            openai_messages = self._convert_messages(messages)
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Error streaming completion: {e}")
            raise

    async def test_connection(self) -> dict:
        """Test connectivity to the LLM provider."""
        try:
            # Try a minimal chat completion
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5,
            )
            return {
                "status": "ok",
                "message": "Connection successful",
                "model": response.model or self.model,
            }
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "model": self.model,
            }
