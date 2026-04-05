"""Tests for application configuration."""

from pathlib import Path

from app.config import Settings, resolve_env_file_path


class TestResolveEnvFilePath:
    def test_finds_env_in_start_directory(self, tmp_path: Path) -> None:
        env_path = tmp_path / ".env"
        env_path.write_text("X=1\n", encoding="utf-8")
        assert resolve_env_file_path(tmp_path) == env_path.resolve()

    def test_finds_env_in_parent(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)
        env_path = tmp_path / ".env"
        env_path.write_text("X=1\n", encoding="utf-8")
        assert resolve_env_file_path(nested) == env_path.resolve()

    def test_returns_none_when_no_env(self, tmp_path: Path) -> None:
        nested = tmp_path / "empty" / "dir"
        nested.mkdir(parents=True)
        assert resolve_env_file_path(nested) is None

    def test_ignores_dotenv_directory(self, tmp_path: Path) -> None:
        bad = tmp_path / ".env"
        bad.mkdir()
        assert resolve_env_file_path(tmp_path) is None


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
        assert settings.inline_monte_carlo_max_iterations == 25
        assert settings.claude_cli_timeout == 120.0
        assert settings.claude_cli_version_check_timeout == 10.0
        assert settings.llm_concurrency_default == 3
        assert settings.llm_concurrency_overrides == ""
        assert settings.debug is False

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        monkeypatch.setenv("LLM_MODEL_NAME", "claude-3-opus")
        monkeypatch.setenv("MCP_SERVER_ENABLED", "true")

        settings = Settings(_env_file=None)
        assert settings.llm_provider == "anthropic"
        assert settings.llm_model_name == "claude-3-opus"
        assert settings.mcp_server_enabled is True

    def test_debug_env_override(self, monkeypatch):
        monkeypatch.setenv("DEBUG", "true")
        settings = Settings(_env_file=None)
        assert settings.debug is True
