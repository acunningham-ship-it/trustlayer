"""Provider registry — discovers and manages all AI providers."""

from .ollama import OllamaProvider
from .openai_compat import OpenAICompatProvider
from ..config import ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY, OLLAMA_BASE_URL


def build_registry(
    anthropic_key: str = "",
    openai_key: str = "",
    google_key: str = "",
    ollama_url: str = "",
) -> dict:
    """Build a registry of all configured providers."""
    registry = {}

    # Always try Ollama (local), using configured URL or default
    registry["ollama"] = OllamaProvider(base_url=ollama_url or OLLAMA_BASE_URL)

    ant_key = anthropic_key or ANTHROPIC_API_KEY
    if ant_key:
        registry["anthropic"] = OpenAICompatProvider("anthropic", ant_key)

    oai_key = openai_key or OPENAI_API_KEY
    if oai_key:
        registry["openai"] = OpenAICompatProvider("openai", oai_key)

    goo_key = google_key or GOOGLE_API_KEY
    if goo_key:
        registry["google"] = OpenAICompatProvider("google", goo_key)

    return registry


# Singleton registry — rebuilt when settings change
_registry = None


def get_registry() -> dict:
    global _registry
    if _registry is None:
        _registry = build_registry()
    return _registry


def rebuild_registry(
    anthropic_key: str = "",
    openai_key: str = "",
    google_key: str = "",
    ollama_url: str = "",
) -> None:
    """Rebuild the provider registry with new API keys (called after settings save)."""
    global _registry
    _registry = build_registry(
        anthropic_key=anthropic_key,
        openai_key=openai_key,
        google_key=google_key,
        ollama_url=ollama_url,
    )
