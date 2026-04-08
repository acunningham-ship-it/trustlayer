"""Cost Tracker — real-time spending dashboard and budget alerts."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone
from typing import Optional

from ..database import get_db, CostEntry, AIInteraction
from ..config import DEFAULT_MONTHLY_BUDGET

router = APIRouter()

# Pricing per 1M tokens (input/output)
PROVIDER_PRICING = {
    "claude-opus-4-6": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.0},
    "gpt-4o": {"input": 5.0, "output": 15.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gemini-2.0-flash": {"input": 0.075, "output": 0.30},
    "gemini-pro": {"input": 0.50, "output": 1.50},
}


@router.get("")
async def costs_root(db=Depends(get_db)):
    """Get cost summary (default root endpoint)."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Monthly total
    result = await db.execute(
        select(func.sum(CostEntry.cost_usd))
        .where(CostEntry.recorded_at >= month_start)
    )
    monthly_total = result.scalar() or 0.0

    # Per-provider breakdown
    result = await db.execute(
        select(CostEntry.provider, func.sum(CostEntry.cost_usd).label("total"))
        .where(CostEntry.recorded_at >= month_start)
        .group_by(CostEntry.provider)
        .order_by(func.sum(CostEntry.cost_usd).desc())
    )
    by_provider = [{"provider": r[0], "cost_usd": round(r[1], 4)} for r in result]

    budget = DEFAULT_MONTHLY_BUDGET
    pct = (monthly_total / budget * 100) if budget > 0 else 0

    return {
        "month": now.strftime("%B %Y"),
        "total_usd": round(monthly_total, 4),
        "budget_usd": budget,
        "budget_pct": round(pct, 1),
        "alert": pct >= 80,
        "alert_message": f"You've spent ${monthly_total:.2f} this month ({pct:.0f}% of your ${budget:.0f} budget)" if pct >= 80 else None,
        "by_provider": by_provider,
    }


@router.get("/summary")
async def cost_summary(db=Depends(get_db)):
    """Get cost summary for current month."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    try:
        # Monthly total
        result = await db.execute(
            select(func.sum(CostEntry.cost_usd))
            .where(CostEntry.recorded_at >= month_start)
        )
        monthly_total = result.scalar() or 0.0

        # Per-provider breakdown
        result = await db.execute(
            select(CostEntry.provider, func.sum(CostEntry.cost_usd).label("total"))
            .where(CostEntry.recorded_at >= month_start)
            .group_by(CostEntry.provider)
            .order_by(func.sum(CostEntry.cost_usd).desc())
        )
        by_provider = [{"provider": r[0], "cost_usd": round(r[1], 4)} for r in result]
    except Exception:
        monthly_total = 0.0
        by_provider = []

    budget = DEFAULT_MONTHLY_BUDGET
    pct = (monthly_total / budget * 100) if budget > 0 else 0

    # Get provider comparison (Ollama vs cloud alternatives)
    provider_comparison = None
    ollama_total = next((p["cost_usd"] for p in by_provider if p["provider"] == "ollama"), 0.0)
    if ollama_total == 0 and any(p["provider"] == "ollama" for p in by_provider):
        # Ollama was used but is free
        result = await db.execute(
            select(func.count().label("count"))
            .select_from(AIInteraction)
            .where(AIInteraction.provider == "ollama")
            .where(AIInteraction.created_at >= month_start)
        )
        ollama_calls = result.scalar() or 0
        if ollama_calls > 0:
            # Estimate savings
            avg_cost_per_call = 0.01  # Rough estimate
            estimated_cloud_cost = ollama_calls * avg_cost_per_call
            provider_comparison = {
                "ollama_calls": ollama_calls,
                "estimated_cloud_cost": round(estimated_cloud_cost, 2),
                "estimated_savings": round(estimated_cloud_cost, 2),
            }

    return {
        "month": now.strftime("%B %Y"),
        "total_usd": round(monthly_total, 4),
        "budget_usd": budget,
        "budget_pct": round(pct, 1),
        "alert": pct >= 80,
        "alert_message": f"You've spent ${monthly_total:.2f} this month ({pct:.0f}% of your ${budget:.0f} budget)" if pct >= 80 else None,
        "by_provider": by_provider,
        "provider_comparison": provider_comparison,
    }


@router.get("/history")
async def cost_history(days: int = 30, db=Depends(get_db)):
    """Get daily cost breakdown for the past N days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(
            func.date(CostEntry.recorded_at).label("date"),
            func.sum(CostEntry.cost_usd).label("total"),
            func.count().label("calls"),
        )
        .where(CostEntry.recorded_at >= since)
        .group_by(func.date(CostEntry.recorded_at))
        .order_by(func.date(CostEntry.recorded_at))
    )
    return [{"date": str(r[0]), "cost_usd": round(r[1], 4), "calls": r[2]} for r in result]


@router.get("/savings")
async def cost_savings(db=Depends(get_db)):
    """Calculate Ollama cost savings vs cloud providers."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    try:
        # Get all Ollama interactions this month
        result = await db.execute(
            select(
                func.sum(AIInteraction.tokens_used).label("total_tokens"),
                func.count().label("call_count"),
            )
            .where(AIInteraction.provider == "ollama")
            .where(AIInteraction.created_at >= month_start)
        )
        row = result.scalar_one_or_none()
    except Exception:
        # Database table doesn't exist yet
        row = None

    if not row or not row[0]:
        return {
            "month": now.strftime("%B %Y"),
            "ollama_interactions": 0,
            "ollama_cost_usd": 0.0,
            "estimated_cloud_costs": {},
            "total_saved_usd": 0.0,
        }

    total_tokens = row[0] or 0
    call_count = row[1] or 0

    # Estimate cost if these calls were made on cloud providers
    # Simple approximation: average tokens per call
    avg_tokens_per_call = total_tokens / call_count if call_count > 0 else total_tokens

    cloud_costs = {}
    for provider_model, pricing in PROVIDER_PRICING.items():
        # Estimate cost: assume 30% input, 70% output
        input_tokens = int(avg_tokens_per_call * 0.3)
        output_tokens = int(avg_tokens_per_call * 0.7)

        input_cost = (input_tokens / 1_000_000) * pricing["input"] * call_count
        output_cost = (output_tokens / 1_000_000) * pricing["output"] * call_count

        cloud_costs[provider_model] = round(input_cost + output_cost, 2)

    total_saved = sum(cloud_costs.values())

    return {
        "month": now.strftime("%B %Y"),
        "ollama_interactions": call_count,
        "ollama_cost_usd": 0.0,
        "total_tokens_saved": total_tokens,
        "estimated_cloud_costs": cloud_costs,
        "total_saved_usd": round(total_saved, 2),
        "breakdown_by_provider": {
            "cheapest": min(cloud_costs.items(), key=lambda x: x[1])[0] if cloud_costs else None,
            "most_expensive": max(cloud_costs.items(), key=lambda x: x[1])[0] if cloud_costs else None,
        },
    }


@router.get("/optimize")
async def cost_optimize(db=Depends(get_db)):
    """Suggest cheaper models for common tasks."""
    try:
        result = await db.execute(
            select(AIInteraction.model, func.avg(AIInteraction.cost_usd).label("avg_cost"))
            .group_by(AIInteraction.model)
            .order_by(func.avg(AIInteraction.cost_usd).desc())
        )
        expensive = [{"model": r[0], "avg_cost_usd": round(r[1], 4)} for r in result]
    except Exception:
        expensive = []

    tips = []
    for item in expensive:
        if "opus" in item["model"].lower():
            tips.append(f"Switch from {item['model']} to claude-sonnet-4-6 to save ~80%")
        elif "gpt-4o" == item["model"]:
            tips.append(f"Use gpt-4o-mini for simple tasks instead of gpt-4o to save ~94%")

    return {"expensive_models": expensive, "tips": tips}
