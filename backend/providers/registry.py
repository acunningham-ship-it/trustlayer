"""Provider registry — discovers and manages all AI providers."""

from .ollama import OllamaProvider
from .openai_compat import OpenAICompatProvider
from ..config import ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY


def build_registry() -> dict:
    """Build a registry of all configured providers."""
    registry = {}

    # Always try Ollama (local)
    registry["ollama"] = OllamaProvider()

    if ANTHROPIC_API_KEY:
        registry["anthropic"] = OpenAICompatProvider("anthropic", ANTHROPIC_API_KEY)

    if OPENAI_API_KEY:
        registry["openai"] = OpenAICompatProvider("openai", OPENAI_API_KEY)

    if GOOGLE_API_KEY:
        registry["google"] = OpenAICompatProvider("google", GOOGLE_API_KEY)

    return registry


# Singleton registry
_registry = None


def get_registry() -> dict:
    global _registry
    if _registry is None:
        _registry = build_registry()
    return _registry
