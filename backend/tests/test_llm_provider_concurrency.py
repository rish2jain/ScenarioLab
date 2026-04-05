"""Tests for per-provider LLM concurrency semaphores."""

import asyncio
from collections.abc import Generator

import pytest

from app.llm import provider as provider_module


@pytest.fixture(autouse=True)
def _reset_semaphores() -> Generator[None, None, None]:
    provider_module.reset_llm_provider_semaphores()
    yield
    provider_module.reset_llm_provider_semaphores()


class TestConcurrencyLimitForProvider:
    def test_default_matches_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LLM_CONCURRENCY_DEFAULT", "7")
        from app.config import Settings

        s = Settings(_env_file=None)
        monkeypatch.setattr(provider_module, "_parse_concurrency_overrides", lambda: {})
        monkeypatch.setattr("app.config.settings", s, raising=False)

        assert provider_module.concurrency_limit_for_provider("openai") == 7

    def test_override_by_provider_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LLM_CONCURRENCY_DEFAULT", "3")
        monkeypatch.setenv(
            "LLM_CONCURRENCY_OVERRIDES",
            '{"cli-claude": 2, "openai": 12}',
        )
        from app.config import Settings

        s = Settings(_env_file=None)
        monkeypatch.setattr("app.config.settings", s, raising=False)

        assert provider_module.concurrency_limit_for_provider("cli-claude") == 2
        assert provider_module.concurrency_limit_for_provider("openai") == 12
        assert provider_module.concurrency_limit_for_provider("ollama") == 3

    def test_keys_are_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "LLM_CONCURRENCY_OVERRIDES",
            '{"CLI-CLAUDE": 4}',
        )
        from app.config import Settings

        s = Settings(_env_file=None)
        monkeypatch.setattr("app.config.settings", s, raising=False)

        assert provider_module.concurrency_limit_for_provider("cli-claude") == 4


class TestGetLlmSemaphore:
    def test_returns_same_instance_per_provider(self) -> None:
        a = provider_module.get_llm_semaphore("openai")
        b = provider_module.get_llm_semaphore("openai")
        assert a is b
        c = provider_module.get_llm_semaphore("anthropic")
        assert c is not a

    async def test_semaphore_enforces_concurrency_limit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LLM_CONCURRENCY_OVERRIDES", '{"openai": 5}')
        from app.config import Settings

        s = Settings(_env_file=None)
        monkeypatch.setattr("app.config.settings", s, raising=False)

        sem = provider_module.get_llm_semaphore("openai")
        assert isinstance(sem, asyncio.Semaphore)

        limit = 5
        for _ in range(limit):
            await asyncio.wait_for(sem.acquire(), timeout=0.1)

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(sem.acquire(), timeout=0.1)
