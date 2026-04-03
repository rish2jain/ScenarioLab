"""Base LLM provider abstraction."""

import asyncio
from abc import ABC, abstractmethod
from typing import AsyncIterator

from pydantic import BaseModel

# Global semaphore to limit concurrent LLM calls across all providers
_llm_semaphore = asyncio.Semaphore(10)

MAX_CONCURRENT_LLM_CALLS = 10
MAX_TOKENS_CAP = 8192


class LLMMessage(BaseModel):
    """Standard message format for LLM interactions."""

    role: str  # "system", "user", "assistant"
    content: str


class LLMResponse(BaseModel):
    """Standard response format from LLM providers."""

    content: str
    model: str
    provider: str
    # usage: {"prompt_tokens": X, "completion_tokens": Y, "total_tokens": Z}
    usage: dict | None = None


class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    provider_name: str

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> LLMResponse:
        """Generate a completion from messages."""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream a completion token by token."""
        pass

    @abstractmethod
    async def test_connection(self) -> dict:
        """Test connectivity.

        Returns {"status": "ok"/"error", "message": "...", "model": "..."}
        """
        pass
