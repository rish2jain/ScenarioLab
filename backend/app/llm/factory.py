"""LLM Provider factory."""

import logging

from app.config import settings
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.cli_chatgpt_provider import CLIChatGPTProvider
from app.llm.cli_claude_provider import CLIClaudeProvider
from app.llm.cli_codex_provider import CLICodexProvider
from app.llm.cli_gemini_provider import CLIGeminiProvider
from app.llm.llamacpp_provider import DEFAULT_LLAMACPP_URL, LlamaCppProvider
from app.llm.ollama_provider import DEFAULT_OLLAMA_URL, OllamaProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.provider import LLMProvider
from app.llm.wizard_models import validate_wizard_model_override

logger = logging.getLogger(__name__)

# Default base URLs for known providers
DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "google": "https://generativelanguage.googleapis.com/v1beta",
    "ollama": DEFAULT_OLLAMA_URL,
    "llamacpp": DEFAULT_LLAMACPP_URL,
}


def _get_cli_model_override() -> str:
    """Return the configured CLI model override, or blank for provider default.

    The repo's shared settings default is still ``gpt-4``. For CLI providers,
    treat that inherited default as "unset" unless the user explicitly set
    ``LLM_MODEL_NAME`` in the environment.
    """
    model = settings.llm_model_name.strip()
    if model == "gpt-4" and "llm_model_name" not in settings.model_fields_set:
        return ""
    return model


def _resolve_cli_model_override(model_override: str | None) -> str:
    """Use explicit override when set; else configured CLI default from settings."""
    if model_override and str(model_override).strip():
        return str(model_override).strip()
    return _get_cli_model_override()


def _effective_model(model_override: str | None) -> str:
    """Use wizard/simulation override when set; else global settings."""
    if model_override and str(model_override).strip():
        return str(model_override).strip()
    return settings.llm_model_name


def _get_base_url(provider: str) -> str:
    """Get the base URL for a provider.

    Uses configured base_url if set, otherwise uses default.
    """
    # If user has explicitly set a base_url, use it
    if settings.llm_base_url and settings.llm_base_url != "https://api.openai.com/v1":
        return settings.llm_base_url

    # Otherwise use provider-specific default
    return DEFAULT_BASE_URLS.get(provider, "https://api.openai.com/v1")


def create_openai_provider(model_override: str | None = None) -> OpenAIProvider:
    """Create an OpenAI-compatible provider."""
    base_url = _get_base_url(settings.llm_provider)
    api_key = settings.llm_api_key

    if not api_key:
        logger.warning(f"No API key set for {settings.llm_provider} provider")

    return OpenAIProvider(
        api_key=api_key,
        base_url=base_url,
        model=_effective_model(model_override),
    )


def create_anthropic_provider(model_override: str | None = None) -> AnthropicProvider:
    """Create an Anthropic provider."""
    api_key = settings.llm_api_key

    if not api_key:
        logger.warning("No API key set for Anthropic provider")

    return AnthropicProvider(
        api_key=api_key,
        model=_effective_model(model_override),
    )


def create_ollama_provider(model_override: str | None = None) -> OllamaProvider:
    """Create an Ollama provider."""
    base_url = _get_base_url("ollama")

    return OllamaProvider(
        model=_effective_model(model_override),
        base_url=base_url,
    )


def create_llamacpp_provider(model_override: str | None = None) -> LlamaCppProvider:
    """Create a llama.cpp provider."""
    base_url = _get_base_url("llamacpp")

    return LlamaCppProvider(
        model=_effective_model(model_override),
        base_url=base_url,
    )


def create_cli_claude_provider(model_override: str | None = None) -> CLIClaudeProvider:
    """Create a Claude CLI provider."""
    return CLIClaudeProvider(model=_resolve_cli_model_override(model_override))


def create_cli_gemini_provider(model_override: str | None = None) -> CLIGeminiProvider:
    """Create a Gemini CLI provider."""
    return CLIGeminiProvider(model=_resolve_cli_model_override(model_override))


def create_cli_chatgpt_provider(
    model_override: str | None = None,
) -> CLIChatGPTProvider:
    """Create a ChatGPT/OpenAI CLI provider."""
    return CLIChatGPTProvider(model=_resolve_cli_model_override(model_override))


def create_cli_codex_provider(model_override: str | None = None) -> CLICodexProvider:
    """Create a Codex CLI provider."""
    return CLICodexProvider(model=_resolve_cli_model_override(model_override))


def _effective_local_model(model_override: str | None) -> str:
    if model_override and str(model_override).strip():
        return str(model_override).strip()
    return settings.local_llm_model_name


def get_local_llm_provider(*, model_override: str | None = None) -> LLMProvider | None:
    """Create the local-tier LLM provider from ``LOCAL_LLM_*`` settings.

    Returns ``None`` when ``local_llm_provider`` is unset/empty (local tier disabled).
    Uses dedicated base URL/model so cloud ``LLM_PROVIDER`` can differ from local.

    ``model_override`` must be a **local** model tag (e.g. Ollama name), not the
    wizard's cloud ``parameters.model``.
    """
    name = (settings.local_llm_provider or "").strip().lower()
    if not name:
        return None

    model = _effective_local_model(model_override)

    if name == "ollama":
        base_url = (settings.local_llm_base_url or "").strip() or DEFAULT_OLLAMA_URL
        return OllamaProvider(model=model, base_url=base_url)
    if name == "llamacpp":
        base_url = (settings.local_llm_base_url or "").strip() or DEFAULT_LLAMACPP_URL
        return LlamaCppProvider(model=model, base_url=base_url)

    logger.warning("Unknown LOCAL_LLM_PROVIDER=%s; local tier disabled", name)
    return None


def get_llm_provider(*, model_override: str | None = None) -> LLMProvider:
    """Create LLM provider based on settings.

    Args:
        model_override: Optional model id from simulation wizard ``parameters.model``.

    Returns:
        An instance of the configured LLM provider.

    Raises:
        ValueError: If the configured provider is not supported or the model id does
            not match the configured provider family.
    """
    validate_wizard_model_override(model_override)
    mo = model_override
    provider_map = {
        "openai": lambda: create_openai_provider(mo),
        "anthropic": lambda: create_anthropic_provider(mo),
        "google": lambda: create_openai_provider(mo),  # Google via OpenAI-compatible
        "qwen": lambda: create_openai_provider(mo),  # Qwen via OpenAI-compatible
        "ollama": lambda: create_ollama_provider(mo),
        "llamacpp": lambda: create_llamacpp_provider(mo),
        "cli-claude": lambda: create_cli_claude_provider(mo),
        "cli-gemini": lambda: create_cli_gemini_provider(mo),
        "cli-chatgpt": lambda: create_cli_chatgpt_provider(mo),
        "cli-codex": lambda: create_cli_codex_provider(mo),
    }

    provider_name = settings.llm_provider.lower()
    creator = provider_map.get(provider_name)

    if not creator:
        raise ValueError(
            f"Unsupported LLM provider: {settings.llm_provider}. " f"Supported providers: {list(provider_map.keys())}"
        )

    logger.info(f"Creating LLM provider: {provider_name}")
    return creator()
