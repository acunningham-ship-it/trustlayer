"""Tests for provider registry and configuration."""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.providers.registry import build_registry
from backend.providers.base import BaseProvider, AIResponse


def test_registry_always_has_ollama():
    """Ollama should always be in the registry (even if not running)."""
    registry = build_registry()
    assert "ollama" in registry


def test_registry_providers_are_base_instances():
    """All registry entries should be BaseProvider subclasses."""
    registry = build_registry()
    for name, provider in registry.items():
        assert isinstance(provider, BaseProvider), f"{name} is not a BaseProvider"


def test_anthropic_only_if_key():
    """Anthropic provider only added when ANTHROPIC_API_KEY is set."""
    import os
    original = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        os.environ.pop("ANTHROPIC_API_KEY", None)
        # Force fresh registry
        import importlib
        import backend.providers.registry as reg_mod
        reg_mod._registry = None
        registry = build_registry()
        if not os.environ.get("ANTHROPIC_API_KEY"):
            assert "anthropic" not in registry
    finally:
        if original:
            os.environ["ANTHROPIC_API_KEY"] = original
        import backend.providers.registry as reg_mod
        reg_mod._registry = None


def test_ai_response_dataclass():
    """AIResponse should be constructable with required fields."""
    r = AIResponse(
        provider="test",
        model="test-model",
        content="Hello",
        tokens_in=10,
        tokens_out=5,
        cost_usd=0.001,
        latency_ms=250,
    )
    assert r.provider == "test"
    assert r.cost_usd == 0.001
    assert r.raw is None
