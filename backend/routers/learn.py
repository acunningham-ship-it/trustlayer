"""Personal Learning — remembers how YOU work across sessions."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, delete
from typing import Optional, Any
from datetime import datetime

from ..database import get_db, UserProfile

router = APIRouter()


class ProfileUpdate(BaseModel):
    key: str
    value: Any


@router.get("/profile")
async def get_profile(db=Depends(get_db)):
    """Get the user's full local profile."""
    result = await db.execute(select(UserProfile))
    items = result.scalars().all()
    return {item.key: item.value for item in items}


@router.put("/profile")
async def update_profile(update: ProfileUpdate, db=Depends(get_db)):
    """Update a profile field."""
    result = await db.execute(
        select(UserProfile).where(UserProfile.key == update.key)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.value = update.value
        existing.updated_at = datetime.utcnow()
    else:
        db.add(UserProfile(key=update.key, value=update.value))

    await db.commit()
    return {"key": update.key, "value": update.value, "saved": True}


@router.delete("/profile/{key}")
async def delete_profile_key(key: str, db=Depends(get_db)):
    """Remove a profile field."""
    await db.execute(delete(UserProfile).where(UserProfile.key == key))
    await db.commit()
    return {"deleted": key}


@router.get("/insights")
async def get_insights(db=Depends(get_db)):
    """Analyze usage patterns and return personalized insights."""
    from ..database import AIInteraction, CostEntry
    from sqlalchemy import func

    # Most used providers
    result = await db.execute(
        select(AIInteraction.provider, func.count().label("count"))
        .group_by(AIInteraction.provider)
        .order_by(func.count().desc())
        .limit(5)
    )
    top_providers = [{"provider": r[0], "count": r[1]} for r in result]

    # Total interactions
    total = await db.execute(select(func.count()).select_from(AIInteraction))
    total_count = total.scalar()

    return {
        "total_interactions": total_count,
        "top_providers": top_providers,
        "personalization_level": min(100, total_count * 2),
        "message": f"After {total_count} sessions, TrustLayer is learning your preferences." if total_count > 0 else "Start using TrustLayer to build your personalized profile.",
    }
