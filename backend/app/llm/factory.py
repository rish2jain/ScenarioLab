"""LLM Provider factory."""

import logging

from app.config import settings
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.cli_chatgpt_provider import CLIChatGPTProvider
from app.llm.cli_claude_provider import CLIClaudeProvider
from app.llm.cli_gemini_provider import CLIGeminiProvider
from app.llm.llamacpp_provider import DEFAULT_LLAMACPP_URL, LlamaCppProvider
from app.llm.ollama_provider import DEFAULT_OLLAMA_URL, OllamaProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

# Default base URLs for known providers
DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "google": "https://generativelanguage.googleapis.com/v1beta",
    "ollama": DEFAULT_OLLAMA_URL,
    "llamacpp": DEFAULT_LLAMACPP_URL,
}


def _get_base_url(provider: str) -> str:
    """Get the base URL for a provider.

    Uses configured base_url if set, otherwise uses default.
    """
    # If user has explicitly set a base_url, use it
    if (
        settings.llm_base_url
        and settings.llm_base_url != "https://api.openai.com/v1"
    ):
        return settings.llm_base_url

    # Otherwise use provider-specific default
    return DEFAULT_BASE_URLS.get(provider, "https://api.openai.com/v1")


def create_openai_provider() -> OpenAIProvider:
    """Create an OpenAI-compatible provider."""
    base_url = _get_base_url(settings.llm_provider)
    api_key = settings.llm_api_key

    if not api_key:
        logger.warning(
            f"No API key set for {settings.llm_provider} provider"
        )

    return OpenAIProvider(
        api_key=api_key,
        base_url=base_url,
        model=settings.llm_model_name,
    )


def create_anthropic_provider() -> AnthropicProvider:
    """Create an Anthropic provider."""
    api_key = settings.llm_api_key

    if not api_key:
        logger.warning("No API key set for Anthropic provider")

    return AnthropicProvider(
        api_key=api_key,
        model=settings.llm_model_name,
    )


def create_ollama_provider() -> OllamaProvider:
    """Create an Ollama provider."""
    base_url = _get_base_url("ollama")

    return OllamaProvider(
        model=settings.llm_model_name,
        base_url=base_url,
    )


def create_llamacpp_provider() -> LlamaCppProvider:
    """Create a llama.cpp provider."""
    base_url = _get_base_url("llamacpp")

    return LlamaCppProvider(
        model=settings.llm_model_name,
        base_url=base_url,
    )


def create_cli_claude_provider() -> CLIClaudeProvider:
    """Create a Claude CLI provider."""
    return CLIClaudeProvider(model=settings.llm_model_name)


def create_cli_gemini_provider() -> CLIGeminiProvider:
    """Create a Gemini CLI provider."""
    return CLIGeminiProvider(model=settings.llm_model_name)


def create_cli_chatgpt_provider() -> CLIChatGPTProvider:
    """Create a ChatGPT/OpenAI CLI provider."""
    return CLIChatGPTProvider(model=settings.llm_model_name)


def get_llm_provider() -> LLMProvider:
    """Create LLM provider based on settings.

    Returns:
        An instance of the configured LLM provider.

    Raises:
        ValueError: If the configured provider is not supported.
    """
    provider_map = {
        "openai": create_openai_provider,
        "anthropic": create_anthropic_provider,
        "google": create_openai_provider,  # Google via OpenAI-compatible
        "qwen": create_openai_provider,  # Qwen via OpenAI-compatible
        "ollama": create_ollama_provider,
        "llamacpp": create_llamacpp_provider,
        "cli-claude": create_cli_claude_provider,
        "cli-gemini": create_cli_gemini_provider,
        "cli-chatgpt": create_cli_chatgpt_provider,
    }

    provider_name = settings.llm_provider.lower()
    creator = provider_map.get(provider_name)

    if not creator:
        raise ValueError(
            f"Unsupported LLM provider: {settings.llm_provider}. "
            f"Supported providers: {list(provider_map.keys())}"
        )

    logger.info(f"Creating LLM provider: {provider_name}")
    return creator()
