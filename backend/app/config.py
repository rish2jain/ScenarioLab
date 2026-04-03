from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LLM
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model_name: str = "gpt-4"

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

    # Voice Settings
    whisper_model: str = "whisper-1"
    tts_voice: str = "alloy"
    tts_model: str = "tts-1"

    # Fine-tuning
    fine_tune_data_dir: str = "./fine_tune_data"
    fine_tune_output_dir: str = "./fine_tune_output"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
