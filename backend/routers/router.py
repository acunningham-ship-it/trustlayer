"""Smart Model Router — AI-powered prompt analysis and auto-routing to best model."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List
import re
import asyncio
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone

from ..database import AIInteraction, get_db
from ..providers.registry import get_registry
from ..routers.verify import TrustScore

router = APIRouter()


class RouteRequest(BaseModel):
    """Request to analyze a prompt and route to best model."""
    prompt: str
    auto_execute: bool = False
    max_tokens: Optional[int] = 1024


class Alternative(BaseModel):
    """Alternative model recommendation."""
    provider: str
    model: str
    reasoning: str
    confidence: float


class RouteResult(BaseModel):
    """Result of routing analysis."""
    task_type: str
    recommended_provider: str
    recommended_model: str
    reasoning: str
    confidence: float
    alternatives: List[Alternative]


# Task type detection patterns
TASK_PATTERNS = {
    "code": [
        r"\bcode\b", r"\bfunction\b", r"\bpython\b", r"\bjavascript\b",
        r"\bdebug\b", r"\bfix.*bug\b", r"\bimplement\b", r"\bclass\b",
        r"\bapi\b", r"\bscript\b", r"\bprogram\b", r"\brefactor\b",
        r"\btest\b", r"\bunit test\b"
    ],
    "creative": [
        r"\bwrite.*story\b", r"\bpoem\b", r"\bcreative\b", r"\bimagine\b",
        r"\bfiction\b", r"\bblog post\b", r"\bscript\b", r"\bnarrative\b",
        r"\bchar\w+ development\b", r"\bscreenplay\b"
    ],
    "analysis": [
        r"\banalyze\b", r"\bsummarize\b", r"\bcompare\b", r"\bevaluate\b",
        r"\breview\b", r"\bassess\b", r"\bexamine\b", r"\bbreak down\b",
        r"\binterpret\b", r"\bexplain.*why\b"
    ],
    "factual": [
        r"\bwhat is\b", r"\bwho is\b", r"\bwhen did\b", r"\bhow does\b",
        r"\bexplain\b", r"\bdefine\b", r"\btell me about\b", r"\binform\b",
        r"\bfact\b", r"\bhistory\b", r"\bbiography\b"
    ],
    "quick": [
        r"\btranslate\b", r"\bconvert\b", r"\bformat\b", r"\blist\b",
        r"\bshort\b", r"\bbrief\b", r"\bquick\b", r"\bsimple\b",
        r"\bfew words\b", r"\bone liner\b"
    ],
}

# Best model recommendations per task type (provider, model, reasoning)
MODEL_RECOMMENDATIONS = {
    "code": {
        "primary": ("anthropic", "claude-sonnet-4-5", "Claude Sonnet excels at code generation, debugging, and technical analysis with strong reasoning"),
        "secondary": ("ollama", "llama3.2", "Local Ollama for code tasks saves API budget and provides offline capability"),
    },
    "creative": {
        "primary": ("openai", "gpt-4o", "GPT-4o shows strong creative writing and narrative generation with vivid details"),
        "secondary": ("anthropic", "claude-sonnet-4-5", "Claude Sonnet provides coherent creative writing with good narrative structure"),
    },
    "analysis": {
        "primary": ("anthropic", "claude-opus-4-5", "Claude Opus provides deep analytical reasoning and comprehensive breakdowns"),
        "secondary": ("anthropic", "claude-sonnet-4-5", "Claude Sonnet balances analytical depth with speed and cost"),
    },
    "factual": {
        "primary": ("ollama", "llama3.2", "Local Ollama is fast and free for factual Q&A — save your API budget for complex tasks"),
        "secondary": ("anthropic", "claude-haiku-4-5", "Claude Haiku provides accurate factual responses at minimal cost"),
    },
    "quick": {
        "primary": ("anthropic", "claude-haiku-4-5", "Claude Haiku is the fastest and cheapest for simple tasks with minimal latency"),
        "secondary": ("openai", "gpt-4o-mini", "GPT-4o-mini provides cost-effective quick responses"),
    },
}


class TaskTypeAnalyzer:
    """Analyze prompt to detect task type."""

    def __init__(self, prompt: str):
        self.prompt = prompt.lower()
        self.scores = {}
        self._analyze()

    def _count_pattern_matches(self, patterns: List[str]) -> int:
        """Count regex pattern matches in prompt."""
        return sum(
            len(re.findall(p, self.prompt, re.IGNORECASE))
            for p in patterns
        )

    def _analyze(self):
        """Score each task type."""
        for task_type, patterns in TASK_PATTERNS.items():
            self.scores[task_type] = self._count_pattern_matches(patterns)

    def get_best_match(self) -> tuple:
        """Return (task_type, score, confidence)."""
        if not self.scores:
            return ("factual", 0, 0.5)

        best_type = max(self.scores, key=self.scores.get)
        best_score = self.scores[best_type]

        # Calculate confidence based on score magnitude
        # 3+ matches = high confidence, 2 = medium, 1 = low, 0 = guess
        if best_score >= 3:
            confidence = 0.95
        elif best_score == 2:
            confidence = 0.75
        elif best_score == 1:
            confidence = 0.50
        else:
            confidence = 0.30

        return (best_type, best_score, confidence)


async def get_model_performance_history(
    db: AsyncSession,
    provider: str,
    model: str,
    task_type: str,
) -> dict:
    """Get historical performance data for a model on this task type."""
    # Get interactions with this model
    result = await db.execute(
        select(
            func.count().label("count"),
            func.avg(AIInteraction.trust_score).label("avg_trust"),
            func.avg(AIInteraction.latency_ms).label("avg_latency"),
            func.avg(AIInteraction.cost_usd).label("avg_cost"),
        )
        .where(AIInteraction.provider == provider)
        .where(AIInteraction.model == model)
    )
    row = result.scalar_one_or_none()

    if not row or not row[0]:
        return {
            "count": 0,
            "avg_trust_score": None,
            "avg_latency_ms": None,
            "avg_cost_usd": None,
        }

    return {
        "count": row[0],
        "avg_trust_score": round(row[1], 1) if row[1] else None,
        "avg_latency_ms": round(row[2], 0) if row[2] else None,
        "avg_cost_usd": round(row[3], 6) if row[3] else None,
    }


@router.post("/suggest")
async def route_suggest(req: RouteRequest, db: AsyncSession = Depends(get_db)):
    """Analyze prompt and suggest best model."""
    analyzer = TaskTypeAnalyzer(req.prompt)
    task_type, score, confidence = analyzer.get_best_match()

    # Get recommendations for this task type
    if task_type not in MODEL_RECOMMENDATIONS:
        task_type = "factual"

    rec = MODEL_RECOMMENDATIONS[task_type]
    primary_provider, primary_model, primary_reasoning = rec["primary"]
    secondary_provider, secondary_model, secondary_reasoning = rec["secondary"]

    # Build alternatives
    alternatives = [
        Alternative(
            provider=secondary_provider,
            model=secondary_model,
            reasoning=secondary_reasoning,
            confidence=0.70,
        )
    ]

    # Get historical performance data
    primary_history = await get_model_performance_history(
        db, primary_provider, primary_model, task_type
    )

    result_data = {
        "task_type": task_type,
        "recommended_provider": primary_provider,
        "recommended_model": primary_model,
        "reasoning": primary_reasoning,
        "confidence": confidence,
        "alternatives": [a.dict() for a in alternatives],
        "pattern_match_score": score,
        "historical_performance": primary_history,
    }

    # If auto_execute, call the recommended model
    if req.auto_execute:
        registry = get_registry()
        provider = registry.get(primary_provider)

        if not provider:
            result_data["auto_execute"] = {
                "status": "error",
                "reason": f"Provider {primary_provider} not available",
            }
        else:
            try:
                response = await provider.complete(
                    req.prompt, primary_model, max_tokens=req.max_tokens
                )

                # Score the response
                scorer = TrustScore(response.content, req.prompt)
                trust = scorer.compute()

                # Record interaction
                interaction = AIInteraction(
                    provider=primary_provider,
                    model=primary_model,
                    prompt=req.prompt,
                    response=response.content,
                    trust_score=trust["score"],
                    tokens_used=response.tokens_out,
                    cost_usd=response.cost_usd,
                    latency_ms=response.latency_ms,
                )
                db.add(interaction)
                await db.commit()

                result_data["auto_execute"] = {
                    "status": "success",
                    "provider": primary_provider,
                    "model": primary_model,
                    "response": response.content,
                    "trust_score": trust["score"],
                    "latency_ms": response.latency_ms,
                    "cost_usd": response.cost_usd,
                    "tokens_out": response.tokens_out,
                }
            except Exception as e:
                result_data["auto_execute"] = {
                    "status": "error",
                    "reason": str(e),
                }

    return result_data


@router.get("/history")
async def route_history(
    task_type: Optional[str] = None,
    provider: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Get routing history — which models were used and their trust scores."""
    query = select(
        AIInteraction.provider,
        AIInteraction.model,
        func.count().label("usage_count"),
        func.avg(AIInteraction.trust_score).label("avg_trust_score"),
        func.min(AIInteraction.trust_score).label("min_trust_score"),
        func.max(AIInteraction.trust_score).label("max_trust_score"),
        func.avg(AIInteraction.cost_usd).label("avg_cost_usd"),
        func.avg(AIInteraction.latency_ms).label("avg_latency_ms"),
    )

    if provider:
        query = query.where(AIInteraction.provider == provider)

    query = query.group_by(AIInteraction.provider, AIInteraction.model)
    query = query.order_by(func.count().desc())
    query = query.limit(limit)

    result = await db.execute(query)
    rows = result.all()

    history = []
    for row in rows:
        history.append(
            {
                "provider": row[0],
                "model": row[1],
                "usage_count": row[2],
                "avg_trust_score": round(row[3], 1) if row[3] else None,
                "min_trust_score": round(row[4], 1) if row[4] else None,
                "max_trust_score": round(row[5], 1) if row[5] else None,
                "avg_cost_usd": round(row[6], 6) if row[6] else None,
                "avg_latency_ms": round(row[7], 0) if row[7] else None,
            }
        )

    return {
        "total_models_used": len(history),
        "history": history,
        "summary": f"You've used {len(history)} models. {history[0]['model']} has the best average trust score ({history[0]['avg_trust_score']}%)" if history else "No routing history yet.",
    }


@router.get("/insights")
async def route_insights(db: AsyncSession = Depends(get_db)):
    """Get insights about routing patterns and recommendations."""
    # Get all interactions
    result = await db.execute(
        select(
            AIInteraction.provider,
            AIInteraction.model,
            func.count().label("count"),
            func.avg(AIInteraction.trust_score).label("avg_trust"),
            func.avg(AIInteraction.cost_usd).label("avg_cost"),
        )
        .group_by(AIInteraction.provider, AIInteraction.model)
        .order_by(func.avg(AIInteraction.trust_score).desc())
    )
    rows = result.all()

    if not rows:
        return {
            "total_interactions": 0,
            "insights": "No interactions recorded yet. Start routing prompts to build insights!",
            "recommendations": [],
        }

    # Group by task patterns (simple heuristic based on model names)
    by_capability = {"code": [], "creative": [], "analysis": [], "factual": [], "quick": []}

    for row in rows:
        model = row[1].lower()
        entry = {
            "provider": row[0],
            "model": row[1],
            "usage": row[2],
            "avg_trust": round(row[3], 1) if row[3] else 0,
            "avg_cost": round(row[4], 6) if row[4] else 0,
        }

        if "opus" in model:
            by_capability["analysis"].append(entry)
        elif "sonnet" in model:
            by_capability["code"].append(entry)
        elif "haiku" in model or "mini" in model:
            by_capability["quick"].append(entry)
        elif "gpt-4o" in model:
            by_capability["creative"].append(entry)
        else:
            by_capability["factual"].append(entry)

    recommendations = []
    for capability, models in by_capability.items():
        if models:
            best = max(models, key=lambda x: x["avg_trust"])
            recommendations.append(
                {
                    "task_type": capability,
                    "recommended_model": best["model"],
                    "provider": best["provider"],
                    "avg_trust_score": best["avg_trust"],
                    "based_on_interactions": best["usage"],
                }
            )

    return {
        "total_interactions": sum(row[2] for row in rows),
        "models_used": len(rows),
        "recommendations": recommendations,
        "summary": "Based on your history, these models perform best for each task type.",
    }
