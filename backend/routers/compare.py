"""Model Comparison — test your tasks against multiple models."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import asyncio
import time

from ..providers.registry import get_registry
from ..routers.verify import TrustScore

router = APIRouter()


class CompareRequest(BaseModel):
    prompt: str
    providers: list[dict]  # [{"provider": "ollama", "model": "llama3.2"}, ...]
    max_tokens: Optional[int] = 1024


@router.post("/")
async def compare_models(req: CompareRequest):
    """Run the same prompt across multiple models and compare results."""
    registry = get_registry()
    results = []

    async def run_one(provider_name: str, model: str):
        provider = registry.get(provider_name)
        if not provider:
            return {"provider": provider_name, "model": model, "error": "Provider not found"}
        try:
            response = await provider.complete(req.prompt, model, max_tokens=req.max_tokens)
            scorer = TrustScore(response.content, req.prompt)
            trust = scorer.compute()
            return {
                "provider": provider_name,
                "model": model,
                "content": response.content,
                "tokens_in": response.tokens_in,
                "tokens_out": response.tokens_out,
                "cost_usd": response.cost_usd,
                "latency_ms": response.latency_ms,
                "trust_score": trust["score"],
                "trust_label": trust["label"],
                "trust_issues": trust["issues"],
            }
        except Exception as e:
            return {"provider": provider_name, "model": model, "error": str(e)}

    tasks = [run_one(p["provider"], p["model"]) for p in req.providers]
    results = await asyncio.gather(*tasks)

    # Rank by trust score desc, then latency asc
    valid = [r for r in results if "error" not in r]
    valid.sort(key=lambda r: (-r["trust_score"], r["latency_ms"]))

    winner = valid[0] if valid else None
    return {
        "results": list(results),
        "ranked": valid,
        "winner": winner,
        "summary": f"Tested {len(req.providers)} models. Best: {winner['provider']}/{winner['model']} with {winner['trust_score']}% trust score." if winner else "No results.",
    }
