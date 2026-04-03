"""Tests for LLM provider factory."""

import os
from unittest.mock import patch

import pytest

from app.llm.factory import (
    DEFAULT_BASE_URLS,
    create_anthropic_provider,
    create_llamacpp_provider,
    create_ollama_provider,
    create_openai_provider,
    get_llm_provider,
)
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.llamacpp_provider import LlamaCppProvider
from app.llm.ollama_provider import OllamaProvider
from app.llm.openai_provider import OpenAIProvider


class TestDefaultBaseUrls:
    def test_known_providers_have_defaults(self):
        assert "openai" in DEFAULT_BASE_URLS
        assert "qwen" in DEFAULT_BASE_URLS
        assert "ollama" in DEFAULT_BASE_URLS
        assert "llamacpp" in DEFAULT_BASE_URLS


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
    def test_case_insensitive(self, mock_settings):
        mock_settings.llm_provider = "OpenAI"
        mock_settings.llm_api_key = "test-key"
        mock_settings.llm_base_url = "https://api.openai.com/v1"
        mock_settings.llm_model_name = "gpt-4"

        provider = get_llm_provider()
        assert isinstance(provider, OpenAIProvider)
