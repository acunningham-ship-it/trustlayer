"""History — browse all past AI interactions and verifications."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from typing import Optional

from ..database import get_db, AIInteraction

router = APIRouter()


@router.get("")
async def list_history(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    provider: Optional[str] = None,
    db=Depends(get_db),
):
    """Get recent interactions with optional provider filter."""
    q = select(AIInteraction).order_by(desc(AIInteraction.created_at))
    if provider:
        q = q.where(AIInteraction.provider == provider)
    q = q.offset(offset).limit(limit)

    result = await db.execute(q)
    items = result.scalars().all()

    return [
        {
            "id": i.id,
            "provider": i.provider,
            "model": i.model,
            "prompt": i.prompt[:200] if i.prompt else "",
            "response": i.response[:300] if i.response else "",
            "trust_score": i.trust_score,
            "tokens_used": i.tokens_used,
            "cost_usd": i.cost_usd,
            "latency_ms": i.latency_ms,
            "created_at": i.created_at.isoformat() if i.created_at else None,
        }
        for i in items
    ]


@router.get("/stats")
async def history_stats(db=Depends(get_db)):
    """Aggregate stats for the history page."""
    total = await db.execute(select(func.count()).select_from(AIInteraction))
    total_count = total.scalar() or 0

    avg_trust = await db.execute(
        select(func.avg(AIInteraction.trust_score)).where(AIInteraction.trust_score.isnot(None))
    )
    avg_trust_val = avg_trust.scalar()

    total_cost = await db.execute(select(func.sum(AIInteraction.cost_usd)))
    total_cost_val = total_cost.scalar() or 0.0

    total_tokens = await db.execute(select(func.sum(AIInteraction.tokens_used)))
    total_tokens_val = total_tokens.scalar() or 0

    providers = await db.execute(
        select(AIInteraction.provider, func.count().label("c"))
        .group_by(AIInteraction.provider)
        .order_by(desc("c"))
    )
    by_provider = [{"provider": r[0], "count": r[1]} for r in providers]

    return {
        "total_interactions": total_count,
        "avg_trust_score": round(avg_trust_val, 1) if avg_trust_val else None,
        "total_cost_usd": round(total_cost_val, 4),
        "total_tokens": total_tokens_val,
        "by_provider": by_provider,
    }


@router.get("/{interaction_id}")
async def get_interaction(interaction_id: str, db=Depends(get_db)):
    """Get full details of a single interaction."""
    result = await db.execute(
        select(AIInteraction).where(AIInteraction.id == interaction_id)
    )
    i = result.scalar_one_or_none()
    if not i:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Interaction not found")

    return {
        "id": i.id,
        "provider": i.provider,
        "model": i.model,
        "prompt": i.prompt,
        "response": i.response,
        "trust_score": i.trust_score,
        "verification_data": i.verification_data,
        "tokens_used": i.tokens_used,
        "cost_usd": i.cost_usd,
        "latency_ms": i.latency_ms,
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }
