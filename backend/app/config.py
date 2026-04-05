from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def resolve_env_file_path(start: Path) -> Path | None:
    """Walk upward from ``start`` until a ``.env`` exists (regular file only)."""
    root = start.resolve()
    for directory in (root, *root.parents):
        candidate = directory / ".env"
        if candidate.is_file():
            return candidate
    return None


# First ``.env`` walking up from this package, or ``None`` (env vars only).
_ENV_FILE = resolve_env_file_path(Path(__file__).resolve().parent)


class Settings(BaseSettings):
    # LLM
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model_name: str = "gpt-4"
    # Max concurrent in-flight LLM generate() calls per provider key (see get_llm_semaphore).
    llm_concurrency_default: int = 3
    # JSON object mapping provider key -> cap, e.g. {"cli-claude":2,"openai":8}
    llm_concurrency_overrides: str = ""
    # cli-gemini: subprocess timeouts (seconds); env overridable
    gemini_cli_timeout: float = 120.0
    gemini_cli_version_check_timeout: float = 5.0
    # cli-claude: subprocess timeouts (seconds); env overridable
    claude_cli_timeout: float = 120.0
    claude_cli_version_check_timeout: float = 10.0

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # Miro
    miro_api_token: str = ""
    miro_board_id: str = ""

    # MCP
    mcp_server_enabled: bool = False

    # Market Intelligence APIs
    alpha_vantage_api_key: str = ""
    news_api_key: str = ""

    # Autoresearch
    tavily_api_key: str = ""
    sec_user_agent: str = "MiroFish/1.0 (research@mirofish.ai)"

    # Optional Zep Cloud (upstream-style graph)
    zep_api_key: str = ""

    # Graph seed extraction: per-seed asyncio.Lock cache (see graph.router)
    graph_seed_extraction_lock_ttl_seconds: float = 3600.0
    graph_seed_extraction_lock_cleanup_interval_seconds: float = 300.0

    # Simulation guardrails
    simulation_max_agents: int = 48
    simulation_llm_parallelism: int = 4
    # Wizard inline Monte Carlo (post-primary batch); must match UI cap in simulations/new
    inline_monte_carlo_max_iterations: int = 25
    # 0 = disabled; otherwise each round is wrapped in asyncio.wait_for
    simulation_round_timeout_seconds: int = 0

    # Voice Settings
    whisper_model: str = "whisper-1"
    tts_voice: str = "alloy"
    tts_model: str = "tts-1"

    # Fine-tuning
    fine_tune_data_dir: str = "./fine_tune_data"
    fine_tune_output_dir: str = "./fine_tune_output"

    # Hybrid inference (optional local tier; see docs/superpowers/specs)
    inference_mode: str = "cloud"  # cloud | hybrid | local
    # ollama | llamacpp — empty disables local tier
    local_llm_provider: str = ""
    local_llm_base_url: str = "http://localhost:11434/v1"
    local_llm_model_name: str = "qwen3:14b"
    hybrid_cloud_rounds: int = 1

    # Integration API: protect /api/v1/api-keys management (Bearer token)
    admin_api_key: str = ""

    # When true, some HTTP error details may include exception messages (dev only).
    debug: bool = False

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE is not None else None,
        env_file_encoding="utf-8",
    )


settings = Settings()
