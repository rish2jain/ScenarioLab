"""Tests for LLM provider factory."""

import logging
from unittest.mock import patch

import pytest

from app.llm.anthropic_provider import AnthropicProvider
from app.llm.cli_chatgpt_provider import CLIChatGPTProvider
from app.llm.cli_claude_provider import CLIClaudeProvider
from app.llm.cli_codex_provider import CLICodexProvider
from app.llm.cli_gemini_provider import CLIGeminiProvider
from app.llm.factory import (
    DEFAULT_BASE_URLS,
    _get_base_url,
    _get_cli_model_override,
    create_anthropic_provider,
    create_cli_chatgpt_provider,
    create_cli_claude_provider,
    create_cli_codex_provider,
    create_cli_gemini_provider,
    create_llamacpp_provider,
    create_ollama_provider,
    create_openai_provider,
    get_llm_provider,
    get_local_llm_provider,
)
from app.llm.llamacpp_provider import DEFAULT_LLAMACPP_URL, LlamaCppProvider
from app.llm.ollama_provider import OllamaProvider
from app.llm.openai_provider import OpenAIProvider


class TestDefaultBaseUrls:
    def test_known_providers_have_defaults(self):
        assert "openai" in DEFAULT_BASE_URLS
        assert "qwen" in DEFAULT_BASE_URLS
        assert "ollama" in DEFAULT_BASE_URLS
        assert "llamacpp" in DEFAULT_BASE_URLS

    def test_google_has_default_url(self):
        assert "google" in DEFAULT_BASE_URLS
        assert DEFAULT_BASE_URLS["google"].startswith("https://")


class TestGetBaseUrl:
    @patch("app.llm.factory.settings")
    def test_returns_explicit_base_url_when_non_default(self, mock_settings):
        mock_settings.llm_base_url = "https://custom.api.example.com/v1"
        url = _get_base_url("openai")
        assert url == "https://custom.api.example.com/v1"

    @patch("app.llm.factory.settings")
    def test_returns_provider_default_when_base_url_is_default_openai(self, mock_settings):
        """When llm_base_url is the OpenAI default, we fall through to provider defaults."""
        mock_settings.llm_base_url = "https://api.openai.com/v1"
        url = _get_base_url("qwen")
        assert "dashscope" in url  # Qwen's default

    @patch("app.llm.factory.settings")
    def test_returns_provider_default_when_base_url_empty(self, mock_settings):
        mock_settings.llm_base_url = ""
        url = _get_base_url("ollama")
        assert url == DEFAULT_BASE_URLS["ollama"]

    @patch("app.llm.factory.settings")
    def test_unknown_provider_falls_back_to_openai_url(self, mock_settings):
        mock_settings.llm_base_url = ""
        url = _get_base_url("unknown-vendor")
        assert url == "https://api.openai.com/v1"


class TestCreateProviders:
    @patch("app.llm.factory.settings")
    def test_create_openai_provider(self, mock_settings):
        mock_settings.llm_provider = "openai"
        mock_settings.llm_api_key = "test-key"
        mock_settings.llm_base_url = "https://api.openai.com/v1"
        mock_settings.llm_model_name = "gpt-4"

        provider = create_openai_provider()
        assert isinstance(provider, OpenAIProvider)
        assert provider.model == "gpt-4"

    @patch("app.llm.factory.settings")
    def test_create_anthropic_provider(self, mock_settings):
        mock_settings.llm_api_key = "test-key"
        mock_settings.llm_model_name = "claude-3-sonnet"

        provider = create_anthropic_provider()
        assert isinstance(provider, AnthropicProvider)

    @patch("app.llm.factory.settings")
    def test_create_ollama_provider(self, mock_settings):
        mock_settings.llm_base_url = ""
        mock_settings.llm_model_name = "llama3"

        provider = create_ollama_provider()
        assert isinstance(provider, OllamaProvider)

    @patch("app.llm.factory.settings")
    def test_create_llamacpp_provider(self, mock_settings):
        mock_settings.llm_base_url = ""
        mock_settings.llm_model_name = "local-model"

        provider = create_llamacpp_provider()
        assert isinstance(provider, LlamaCppProvider)

    @patch("app.llm.factory.settings")
    def test_create_cli_claude_provider(self, mock_settings):
        mock_settings.llm_model_name = "claude-3-5-sonnet-20241022"
        provider = create_cli_claude_provider()
        assert isinstance(provider, CLIClaudeProvider)

    @patch("app.llm.factory.settings")
    def test_create_cli_gemini_provider(self, mock_settings):
        mock_settings.llm_model_name = "gemini-2.0-flash"
        provider = create_cli_gemini_provider()
        assert isinstance(provider, CLIGeminiProvider)

    def test_cli_gemini_provider_accepts_gemini_prefix_case_insensitive(self):
        """Model names must match 'gemini' prefix case-insensitively (like cli-claude)."""
        p = CLIGeminiProvider(model="GEMINI-2.0-flash")
        assert p.model == "GEMINI-2.0-flash"

    @patch("app.llm.factory.settings")
    def test_create_cli_chatgpt_provider(self, mock_settings):
        mock_settings.llm_model_name = "gpt-4o"
        provider = create_cli_chatgpt_provider()
        assert isinstance(provider, CLIChatGPTProvider)

    @patch("app.llm.factory.settings")
    def test_create_cli_codex_provider(self, mock_settings):
        mock_settings.llm_model_name = "gpt-5.4"
        provider = create_cli_codex_provider()
        assert isinstance(provider, CLICodexProvider)


class TestGetLLMProvider:
    @patch("app.llm.factory.settings")
    def test_openai_provider(self, mock_settings):
        mock_settings.llm_provider = "openai"
        mock_settings.llm_api_key = "test-key"
        mock_settings.llm_base_url = "https://api.openai.com/v1"
        mock_settings.llm_model_name = "gpt-4"

        provider = get_llm_provider()
        assert isinstance(provider, OpenAIProvider)

    @patch("app.llm.factory.settings")
    def test_model_override_openai(self, mock_settings):
        mock_settings.llm_provider = "openai"
        mock_settings.llm_api_key = "test-key"
        mock_settings.llm_base_url = "https://api.openai.com/v1"
        mock_settings.llm_model_name = "gpt-4"

        provider = get_llm_provider(model_override="gpt-4o-mini")
        assert isinstance(provider, OpenAIProvider)
        assert provider.model == "gpt-4o-mini"

    @patch("app.llm.factory.settings")
    def test_anthropic_provider(self, mock_settings):
        mock_settings.llm_provider = "anthropic"
        mock_settings.llm_api_key = "test-key"
        mock_settings.llm_model_name = "claude-3-sonnet"

        provider = get_llm_provider()
        assert isinstance(provider, AnthropicProvider)

    @patch("app.llm.factory.settings")
    def test_google_uses_openai_compat(self, mock_settings):
        mock_settings.llm_provider = "google"
        mock_settings.llm_api_key = "test-key"
        mock_settings.llm_base_url = ""
        mock_settings.llm_model_name = "gemini-pro"

        provider = get_llm_provider()
        assert isinstance(provider, OpenAIProvider)

    @patch("app.llm.factory.settings")
    def test_qwen_uses_openai_compat(self, mock_settings):
        mock_settings.llm_provider = "qwen"
        mock_settings.llm_api_key = "test-key"
        mock_settings.llm_base_url = ""
        mock_settings.llm_model_name = "qwen-72b"

        provider = get_llm_provider()
        assert isinstance(provider, OpenAIProvider)

    @patch("app.llm.factory.settings")
    def test_unsupported_provider_raises(self, mock_settings):
        mock_settings.llm_provider = "nonexistent"

        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            get_llm_provider()

    @patch("app.llm.factory.settings")
    def test_unsupported_provider_error_lists_valid_options(self, mock_settings):
        mock_settings.llm_provider = "fake-vendor"
        with pytest.raises(ValueError) as exc_info:
            get_llm_provider()
        assert "openai" in str(exc_info.value).lower()

    @patch("app.llm.factory.settings")
    def test_case_insensitive(self, mock_settings):
        mock_settings.llm_provider = "OpenAI"
        mock_settings.llm_api_key = "test-key"
        mock_settings.llm_base_url = "https://api.openai.com/v1"
        mock_settings.llm_model_name = "gpt-4"

        provider = get_llm_provider()
        assert isinstance(provider, OpenAIProvider)

    @patch("app.llm.factory.settings")
    def test_missing_api_key_logs_warning(self, mock_settings, caplog):
        mock_settings.llm_provider = "openai"
        mock_settings.llm_api_key = ""  # empty
        mock_settings.llm_base_url = "https://api.openai.com/v1"
        mock_settings.llm_model_name = "gpt-4"

        with caplog.at_level(logging.WARNING, logger="app.llm.factory"):
            provider = get_llm_provider()

        # Provider still created
        assert isinstance(provider, OpenAIProvider)
        # Warning logged
        assert any("api key" in r.message.lower() for r in caplog.records)

    @patch("app.llm.factory.settings")
    def test_cli_claude_provider(self, mock_settings):
        mock_settings.llm_provider = "cli-claude"
        mock_settings.llm_model_name = "claude-3-5-sonnet-20241022"

        provider = get_llm_provider()
        assert isinstance(provider, CLIClaudeProvider)

    @patch("app.llm.factory.settings")
    def test_cli_gemini_provider(self, mock_settings):
        mock_settings.llm_provider = "cli-gemini"
        mock_settings.llm_model_name = "gemini-2.0-flash"

        provider = get_llm_provider()
        assert isinstance(provider, CLIGeminiProvider)

    @patch("app.llm.factory.settings")
    def test_cli_chatgpt_provider(self, mock_settings):
        mock_settings.llm_provider = "cli-chatgpt"
        mock_settings.llm_model_name = "gpt-4o"

        provider = get_llm_provider()
        assert isinstance(provider, CLIChatGPTProvider)

    @patch("app.llm.factory.settings")
    def test_cli_codex_provider(self, mock_settings):
        mock_settings.llm_provider = "cli-codex"
        mock_settings.llm_model_name = "gpt-5.4"

        provider = get_llm_provider()
        assert isinstance(provider, CLICodexProvider)

    @patch("app.llm.factory.settings")
    def test_model_override_mismatch_raises(self, mock_settings):
        mock_settings.llm_provider = "openai"
        mock_settings.llm_api_key = "test-key"
        mock_settings.llm_base_url = "https://api.openai.com/v1"
        mock_settings.llm_model_name = "gpt-4"

        with pytest.raises(ValueError, match="OpenAI-class"):
            get_llm_provider(model_override="claude-3-opus-20240229")


class TestGetCliModelOverride:
    @patch("app.llm.factory.settings")
    def test_gpt4_inherited_default_treated_as_unset(self, mock_settings):
        mock_settings.llm_model_name = "gpt-4"
        mock_settings.model_fields_set = set()
        assert _get_cli_model_override() == ""

    @patch("app.llm.factory.settings")
    def test_gpt4_explicitly_set_returns_model(self, mock_settings):
        mock_settings.llm_model_name = "gpt-4"
        mock_settings.model_fields_set = {"llm_model_name"}
        assert _get_cli_model_override() == "gpt-4"


class TestGetLocalLlmProvider:
    @patch("app.llm.factory.settings")
    def test_empty_local_provider_returns_none(self, mock_settings):
        mock_settings.local_llm_provider = ""
        mock_settings.local_llm_base_url = "http://localhost:11434/v1"
        mock_settings.local_llm_model_name = "qwen3:14b"
        assert get_local_llm_provider() is None

    @patch("app.llm.factory.settings")
    def test_ollama_uses_local_settings(self, mock_settings):
        mock_settings.local_llm_provider = "ollama"
        mock_settings.local_llm_base_url = "http://127.0.0.1:11434/v1"
        mock_settings.local_llm_model_name = "mistral"
        p = get_local_llm_provider()
        assert p is not None
        assert p.provider_name == "ollama"
        assert p.model == "mistral"
        assert "127.0.0.1" in p.base_url

    @patch("app.llm.factory.settings")
    def test_llamacpp_uses_default_base_when_unset(self, mock_settings):
        mock_settings.local_llm_provider = "llamacpp"
        mock_settings.local_llm_base_url = ""
        mock_settings.local_llm_model_name = "foo"
        p = get_local_llm_provider()
        assert p is not None
        assert p.provider_name == "llamacpp"
        assert p.base_url == DEFAULT_LLAMACPP_URL

    @patch("app.llm.factory.settings")
    def test_model_override(self, mock_settings):
        mock_settings.local_llm_provider = "ollama"
        mock_settings.local_llm_base_url = "http://localhost:11434/v1"
        mock_settings.local_llm_model_name = "qwen3:14b"
        p = get_local_llm_provider(model_override="custom-model")
        assert p.model == "custom-model"
