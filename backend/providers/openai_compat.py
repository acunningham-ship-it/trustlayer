"""OpenAI-compatible provider (works with Anthropic, OpenAI, Google via openai SDK)."""

import time
import httpx
from .base import BaseProvider, AIResponse

# Pricing per 1M tokens (input, output) USD
PRICING = {
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5-20251001": (0.25, 1.25),
    "claude-opus-4-6": (15.0, 75.0),
    "gpt-4o": (2.5, 10.0),
    "gpt-4o-mini": (0.15, 0.6),
    "gpt-4.1": (2.0, 8.0),
    "gemini-2.0-flash": (0.1, 0.4),
    "gemini-1.5-pro": (1.25, 5.0),
}

PROVIDER_ENDPOINTS = {
    "anthropic": "https://api.anthropic.com/v1",
    "openai": "https://api.openai.com/v1",
    "google": "https://generativelanguage.googleapis.com/v1beta/openai",
}


class OpenAICompatProvider(BaseProvider):
    """Calls any OpenAI-compatible API endpoint."""

    def __init__(self, provider_name: str, api_key: str, base_url: str = None):
        self.name = provider_name
        self.api_key = api_key
        self.base_url = base_url or PROVIDER_ENDPOINTS.get(provider_name, "")

    async def is_available(self) -> bool:
        return bool(self.api_key and self.base_url)

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                data = r.json()
                return [m["id"] for m in data.get("data", [])]
        except Exception:
            return []

    async def complete(self, prompt: str, model: str, **kwargs) -> AIResponse:
        start = time.time()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.name == "anthropic":
            headers["anthropic-version"] = "2023-06-01"

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": kwargs.get("max_tokens", 2048),
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                f"{self.base_url}/messages" if self.name == "anthropic" else f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            r.raise_for_status()
            data = r.json()

        latency = int((time.time() - start) * 1000)

        if self.name == "anthropic":
            content = data["content"][0]["text"]
            tokens_in = data["usage"]["input_tokens"]
            tokens_out = data["usage"]["output_tokens"]
        else:
            content = data["choices"][0]["message"]["content"]
            tokens_in = data["usage"]["prompt_tokens"]
            tokens_out = data["usage"]["completion_tokens"]

        price_in, price_out = PRICING.get(model, (0, 0))
        cost = (tokens_in * price_in + tokens_out * price_out) / 1_000_000

        return AIResponse(
            provider=self.name,
            model=model,
            content=content,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost,
            latency_ms=latency,
            raw=data,
        )
