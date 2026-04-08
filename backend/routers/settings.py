"""Settings router — runtime configuration management."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from ..database import get_db, UserProfile

router = APIRouter()


class BudgetUpdate(BaseModel):
    budget: float


class OllamaUpdate(BaseModel):
    url: str


@router.get("")
async def get_settings(db=Depends(get_db)):
    """Get current configuration settings (budget, ollama_url, api keys status)."""
    settings = {}

    # Fetch all settings from database
    result = await db.execute(select(UserProfile).filter(UserProfile.key.startswith("settings.")))
    rows = result.scalars().all()

    for row in rows:
        # Extract setting name from key (e.g., "settings.budget" -> "budget")
        setting_name = row.key.replace("settings.", "")
        value = row.value

        # For API keys, return boolean indicating if set
        if setting_name.endswith("_key"):
            settings[setting_name] = bool(value and value.get("value"))
        else:
            settings[setting_name] = value.get("value") if isinstance(value, dict) else value

    # Provide defaults if not set
    return {
        "budget": settings.get("budget", 10.0),
        "ollama_url": settings.get("ollama_url", "http://localhost:11434"),
        "api_keys_set": {
            "openai": settings.get("openai_key", False),
            "anthropic": settings.get("anthropic_key", False),
        },
    }


@router.put("/budget")
async def update_budget(update: BudgetUpdate, db=Depends(get_db)):
    """Update monthly budget setting."""
    if update.budget < 0:
        raise HTTPException(status_code=400, detail="Budget must be non-negative")

    # Check if settings.budget exists
    result = await db.execute(select(UserProfile).filter(UserProfile.key == "settings.budget"))
    profile = result.scalar()

    if profile:
        profile.value = {"value": update.budget}
    else:
        profile = UserProfile(key="settings.budget", value={"value": update.budget})
        db.add(profile)

    await db.commit()
    return {"budget": update.budget}


@router.put("/ollama")
async def update_ollama(update: OllamaUpdate, db=Depends(get_db)):
    """Update Ollama API endpoint URL."""
    if not update.url.strip():
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    # Check if settings.ollama_url exists
    result = await db.execute(select(UserProfile).filter(UserProfile.key == "settings.ollama_url"))
    profile = result.scalar()

    if profile:
        profile.value = {"value": update.url}
    else:
        profile = UserProfile(key="settings.ollama_url", value={"value": update.url})
        db.add(profile)

    await db.commit()
    return {"ollama_url": update.url}
