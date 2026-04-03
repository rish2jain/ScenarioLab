"""Tests for application configuration."""

from app.config import Settings


class TestSettings:
    def test_default_values(self):
        settings = Settings(
            _env_file=None,  # Don't read .env for tests
        )
        assert settings.llm_provider == "openai"
        assert settings.llm_base_url == "https://api.openai.com/v1"
        assert settings.llm_model_name == "gpt-4"
        assert settings.neo4j_uri == "bolt://localhost:7687"
        assert settings.neo4j_user == "neo4j"
        assert settings.mcp_server_enabled is False

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("LLM_MODEL_NAME", "claude-3-opus")
        monkeypatch.setenv("MCP_SERVER_ENABLED", "true")

        settings = Settings(_env_file=None)
        assert settings.llm_provider == "anthropic"
        assert settings.llm_model_name == "claude-3-opus"
        assert settings.mcp_server_enabled is True
