"""Tests for wizard model validation and cost-estimator provider mapping."""

from datetime import datetime
from unittest.mock import patch

import pytest

import app.llm.wizard_models as wizard_models_mod
from app.llm.wizard_models import (
    WIZARD_PROVIDER_DEFAULT_OPTION,
    cost_estimator_provider_key,
    provider_family,
    reset_anthropic_wizard_models_cache,
    validate_wizard_model_override,
    wizard_model_options,
)


@pytest.fixture(autouse=True)
def _reset_anthropic_wizard_cache():
    reset_anthropic_wizard_models_cache()
    yield
    reset_anthropic_wizard_models_cache()


class TestValidateWizardModelOverride:
    @patch("app.llm.wizard_models.settings")
    def test_openai_accepts_gpt(self, mock_settings):
        mock_settings.llm_provider = "openai"
        validate_wizard_model_override("gpt-4o")

    @patch("app.llm.wizard_models.settings")
    def test_openai_rejects_claude(self, mock_settings):
        mock_settings.llm_provider = "openai"
        with pytest.raises(ValueError, match="OpenAI-class"):
            validate_wizard_model_override("claude-3-5-sonnet-20241022")

    @patch("app.llm.wizard_models.settings")
    def test_anthropic_accepts_claude(self, mock_settings):
        mock_settings.llm_provider = "anthropic"
        validate_wizard_model_override("claude-3-opus-20240229")

    @patch("app.llm.wizard_models.settings")
    def test_anthropic_rejects_gpt(self, mock_settings):
        mock_settings.llm_provider = "anthropic"
        with pytest.raises(ValueError, match="Anthropic"):
            validate_wizard_model_override("gpt-4")

    @patch("app.llm.wizard_models.settings")
    def test_ollama_allows_any_model_string(self, mock_settings):
        mock_settings.llm_provider = "ollama"
        validate_wizard_model_override("mistral:latest")

    @patch("app.llm.wizard_models.settings")
    def test_ollama_rejects_stale_cloud_wizard_id(self, mock_settings):
        mock_settings.llm_provider = "ollama"
        with pytest.raises(ValueError, match="cloud API model id"):
            validate_wizard_model_override("gpt-4o")

    @patch("app.llm.wizard_models.settings")
    def test_llamacpp_rejects_claude_id(self, mock_settings):
        mock_settings.llm_provider = "llamacpp"
        with pytest.raises(ValueError, match="cloud API model id"):
            validate_wizard_model_override("claude-3-5-sonnet-20241022")

    @patch("app.llm.wizard_models.settings")
    def test_empty_override_ok(self, mock_settings):
        mock_settings.llm_provider = "openai"
        validate_wizard_model_override("")
        validate_wizard_model_override(None)


class TestProviderFamily:
    @patch("app.llm.wizard_models.settings")
    def test_unknown_provider_logs_warning_and_defaults_openai(self, mock_settings, caplog):
        import logging

        mock_settings.llm_provider = "not-a-real-provider"
        with caplog.at_level(logging.WARNING, logger="app.llm.wizard_models"):
            assert provider_family() == "openai"
        assert "not-a-real-provider" in caplog.text
        assert "Unknown llm_provider" in caplog.text


class TestCostEstimatorProviderKey:
    @patch("app.llm.wizard_models.settings")
    def test_cli_claude_maps_to_anthropic_pricing(self, mock_settings):
        mock_settings.llm_provider = "cli-claude"
        assert cost_estimator_provider_key() == "anthropic"

    @patch("app.llm.wizard_models.settings")
    def test_ollama_maps_to_ollama_costs(self, mock_settings):
        mock_settings.llm_provider = "ollama"
        assert cost_estimator_provider_key() == "ollama"


class TestAnthropicWizardModelCatalog:
    @patch("app.llm.wizard_models.settings")
    def test_stable_fallback_when_no_api_key(self, mock_settings):
        mock_settings.llm_provider = "anthropic"
        mock_settings.llm_api_key = ""
        opts = wizard_model_options()
        assert opts[0] == WIZARD_PROVIDER_DEFAULT_OPTION
        assert opts[1]["id"] == "claude-3-5-sonnet-20241022"
        assert opts[2]["id"] == "claude-opus-4-20250514"
        assert opts[3]["id"] == "claude-3-5-haiku-20241022"

    @patch("app.llm.wizard_models.settings")
    def test_models_api_picks_latest_sonnet_by_created_at(self, mock_settings):
        mock_settings.llm_provider = "anthropic"
        mock_settings.llm_api_key = "sk-test"

        class _M:
            def __init__(self, mid: str, display_name: str, created_at: datetime):
                self.id = mid
                self.display_name = display_name
                self.created_at = created_at

        models = [
            _M("claude-sonnet-a", "A", datetime(2020, 1, 1)),
            _M("claude-sonnet-b", "B", datetime(2025, 6, 1)),
            _M("claude-opus-x", "Opus", datetime(2025, 1, 1)),
            _M("claude-haiku-x", "Haiku", datetime(2025, 1, 1)),
        ]
        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value.models.list.return_value = models
            opts = wizard_model_options()
        assert opts[1]["id"] == "claude-sonnet-b"
        assert opts[1]["name"] == "B"


class TestWizardModelOptions:
    @patch("app.llm.wizard_models.settings")
    def test_openai_returns_gpt_models(self, mock_settings):
        mock_settings.llm_provider = "openai"
        opts = wizard_model_options()
        assert opts[0] == WIZARD_PROVIDER_DEFAULT_OPTION
        assert any("gpt" in o["id"].lower() for o in opts)
        assert not any("claude" in o["id"].lower() for o in opts)

    @patch("app.llm.wizard_models.settings")
    def test_anthropic_prepends_provider_default(self, mock_settings):
        mock_settings.llm_provider = "anthropic"
        mock_settings.llm_api_key = "sk-test"
        opts = wizard_model_options()
        assert opts[0] == WIZARD_PROVIDER_DEFAULT_OPTION
        assert any("claude" in o["id"] for o in opts)

    @patch("app.llm.wizard_models.settings")
    def test_local_returns_empty(self, mock_settings):
        mock_settings.llm_provider = "ollama"
        assert wizard_model_options() == []


class TestAnthropicWizardModelsFallback:
    """Guards _ANTHROPIC_WIZARD_MODELS_FALLBACK shape; update when bumping Claude families (see module doc)."""

    def test_fallback_entries_are_claude_slots_with_keys(self):
        fb = wizard_models_mod._ANTHROPIC_WIZARD_MODELS_FALLBACK
        assert len(fb) >= 3
        for row in fb:
            assert set(row.keys()) == {"id", "name", "desc"}
            assert row["id"].strip()
            assert "claude" in row["id"].lower()
        ids_l = [r["id"].lower() for r in fb]
        assert any("sonnet" in i for i in ids_l)
        assert any("opus" in i for i in ids_l)
        assert any("haiku" in i for i in ids_l)
