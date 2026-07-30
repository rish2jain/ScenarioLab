"""OpenAI/Anthropic clients must use configured HTTP timeouts."""

from unittest.mock import MagicMock, patch

from app.config import Settings


def test_openai_provider_passes_http_timeout():
    settings = Settings(_env_file=None)
    settings.llm_http_timeout = 42.0

    with (
        patch("app.llm.openai_provider.settings", settings),
        patch("app.llm.openai_provider.AsyncOpenAI") as client_cls,
    ):
        client_cls.return_value = MagicMock()
        from app.llm.openai_provider import OpenAIProvider

        OpenAIProvider(api_key="k", base_url="https://example.com/v1", model="m")

    kwargs = client_cls.call_args.kwargs
    assert kwargs["timeout"] == 42.0


def test_anthropic_provider_passes_http_timeout():
    settings = Settings(_env_file=None)
    settings.llm_http_timeout = 33.0

    with (
        patch("app.llm.anthropic_provider.settings", settings),
        patch("app.llm.anthropic_provider.anthropic.AsyncAnthropic") as client_cls,
    ):
        client_cls.return_value = MagicMock()
        from app.llm.anthropic_provider import AnthropicProvider

        AnthropicProvider(api_key="k", model="m")

    kwargs = client_cls.call_args.kwargs
    assert kwargs["timeout"] == 33.0
