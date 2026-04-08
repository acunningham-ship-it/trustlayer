"""Universal AI Connector — manage and query AI providers."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from ..providers.registry import get_registry

router = APIRouter()


class CompleteRequest(BaseModel):
    provider: str
    model: str
    prompt: str
    max_tokens: Optional[int] = 2048


@router.get("/")
async def list_connectors():
    """List all configured AI providers and their availability."""
    registry = get_registry()
    results = []
    for name, provider in registry.items():
        available = await provider.is_available()
        models = await provider.list_models() if available else []
        results.append({
            "name": name,
            "available": available,
            "models": models[:10],  # Cap for response size
        })
    return results


@router.post("/complete")
async def complete(req: CompleteRequest):
    """Run a completion on any connected provider."""
    registry = get_registry()
    provider = registry.get(req.provider)
    if not provider:
        return {"error": f"Provider '{req.provider}' not found"}

    response = await provider.complete(req.prompt, req.model, max_tokens=req.max_tokens)
    return {
        "provider": response.provider,
        "model": response.model,
        "content": response.content,
        "tokens_in": response.tokens_in,
        "tokens_out": response.tokens_out,
        "cost_usd": response.cost_usd,
        "latency_ms": response.latency_ms,
    }


@router.get("/detect")
async def auto_detect():
    """Auto-detect available AI tools on this machine."""
    import shutil
    detected = {}

    # Check CLI tools
    for tool in ["ollama", "claude", "aider", "gemini"]:
        detected[tool] = shutil.which(tool) is not None

    # Check Ollama API
    registry = get_registry()
    detected["ollama_api"] = await registry["ollama"].is_available()

    return detected
