"""Anthropic Claude LLM provider."""

import logging
from typing import AsyncIterator

import anthropic
from anthropic import APIConnectionError, APITimeoutError, RateLimitError
from anthropic.types import Message
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


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""

    provider_name = "anthropic"

    def __init__(self, api_key: str, model: str):
        """Initialize the Anthropic provider.

        Args:
            api_key: API key for authentication
            model: Model name to use (e.g., "claude-3-opus-20240229")
        """
        self.api_key = api_key
        self.model = model
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        logger.info(
            f"Initialized Anthropic provider with model: {model}"
        )

    def _convert_messages(
        self, messages: list[LLMMessage]
    ) -> tuple[str, list[dict]]:
        """Convert LLMMessage objects to Anthropic format.

        Returns:
            Tuple of (system_message, conversation_messages)
        """
        system_message = ""
        conversation_messages = []

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            elif msg.role in ("user", "assistant"):
                conversation_messages.append(
                    {"role": msg.role, "content": msg.content}
                )

        return system_message, conversation_messages

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
            system_msg, conversation = self._convert_messages(messages)

            request_kwargs = {
                "model": self.model,
                "messages": conversation,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs,
            }
            if system_msg:
                request_kwargs["system"] = system_msg

            response: Message = (
                await self.client.messages.create(**request_kwargs)
            )

            content = ""
            if response.content:
                content = response.content[0].text

            usage = None
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": (
                        response.usage.input_tokens
                        + response.usage.output_tokens
                    ),
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
            system_msg, conversation = self._convert_messages(messages)

            request_kwargs = {
                "model": self.model,
                "messages": conversation,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
                **kwargs,
            }
            if system_msg:
                request_kwargs["system"] = system_msg

            async with self.client.messages.stream(**request_kwargs) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error(f"Error streaming completion: {e}")
            raise

    async def test_connection(self) -> dict:
        """Test connectivity to the Anthropic API."""
        try:
            # Try a minimal message
            response = await self.client.messages.create(
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
