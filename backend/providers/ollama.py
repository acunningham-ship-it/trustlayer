"""Ollama local model provider."""

import time
import httpx
from .base import BaseProvider, AIResponse
from ..config import OLLAMA_BASE_URL


class OllamaProvider(BaseProvider):
    name = "ollama"

    def __init__(self, base_url: str = ""):
        self.base_url = base_url or OLLAMA_BASE_URL

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                data = r.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    async def complete(self, prompt: str, model: str = "llama3.2", **kwargs) -> AIResponse:
        start = time.time()
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                f"{self.base_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )
            r.raise_for_status()
            data = r.json()
        latency = int((time.time() - start) * 1000)
        tokens_in = data.get("prompt_eval_count", 0)
        tokens_out = data.get("eval_count", 0)
        return AIResponse(
            provider="ollama",
            model=model,
            content=data.get("response", ""),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=0.0,  # Local = free
            latency_ms=latency,
            raw=data,
        )
