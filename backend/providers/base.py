"""Base AI provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class AIResponse:
    provider: str
    model: str
    content: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: int
    raw: Optional[dict] = None


class BaseProvider(ABC):
    """Abstract base for all AI providers."""

    name: str = ""

    @abstractmethod
    async def complete(self, prompt: str, model: str, **kwargs) -> AIResponse:
        """Generate a completion."""

    @abstractmethod
    async def list_models(self) -> list[str]:
        """List available models."""

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if provider is reachable."""
