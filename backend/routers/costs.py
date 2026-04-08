"""Cost Tracker — real-time spending dashboard and budget alerts."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from datetime import datetime, timedelta
from typing import Optional

from ..database import get_db, CostEntry, AIInteraction
from ..config import DEFAULT_MONTHLY_BUDGET

router = APIRouter()


@router.get("/summary")
async def cost_summary(db=Depends(get_db)):
    """Get cost summary for current month."""
    now = datetime.utcnow()
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


@router.get("/history")
async def cost_history(days: int = 30, db=Depends(get_db)):
    """Get daily cost breakdown for the past N days."""
    since = datetime.utcnow() - timedelta(days=days)
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


@router.get("/optimize")
async def cost_optimize(db=Depends(get_db)):
    """Suggest cheaper models for common tasks."""
    result = await db.execute(
        select(AIInteraction.model, func.avg(AIInteraction.cost_usd).label("avg_cost"))
        .group_by(AIInteraction.model)
        .order_by(func.avg(AIInteraction.cost_usd).desc())
    )
    expensive = [{"model": r[0], "avg_cost_usd": round(r[1], 4)} for r in result]

    tips = []
    for item in expensive:
        if "opus" in item["model"].lower():
            tips.append(f"Switch from {item['model']} to claude-sonnet-4-6 to save ~80%")
        elif "gpt-4o" == item["model"]:
            tips.append(f"Use gpt-4o-mini for simple tasks instead of gpt-4o to save ~94%")

    return {"expensive_models": expensive, "tips": tips}
