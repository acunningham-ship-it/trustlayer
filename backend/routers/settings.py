"""Settings router — runtime configuration management."""

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from ..database import get_db, UserProfile

router = APIRouter()


class BudgetUpdate(BaseModel):
    budget: float


class OllamaUpdate(BaseModel):
    url: str


class SettingsUpdate(BaseModel):
    apiKeys: dict = {}
    budget: float | None = None


class ProviderTest(BaseModel):
    apiKey: str | None = None
    baseUrl: str | None = None


@router.get("")
async def get_settings(db=Depends(get_db)):
    """Get current configuration settings (apiKeys and budget)."""
    settings = {
        "apiKeys": {
            "anthropic": "",
            "openai": "",
            "google": "",
            "ollamaBaseUrl": ""
        },
        "budget": None
    }

    # Fetch all settings from database
    result = await db.execute(select(UserProfile).filter(UserProfile.key.startswith("settings.")))
    rows = result.scalars().all()

    for row in rows:
        setting_name = row.key.replace("settings.", "")
        value = row.value

        if setting_name == "budget":
            settings["budget"] = value.get("value") if isinstance(value, dict) else value
        elif setting_name == "anthropic_key":
            settings["apiKeys"]["anthropic"] = value.get("value", "") if isinstance(value, dict) else ""
        elif setting_name == "openai_key":
            settings["apiKeys"]["openai"] = value.get("value", "") if isinstance(value, dict) else ""
        elif setting_name == "google_key":
            settings["apiKeys"]["google"] = value.get("value", "") if isinstance(value, dict) else ""
        elif setting_name == "ollama_url":
            settings["apiKeys"]["ollamaBaseUrl"] = value.get("value", "") if isinstance(value, dict) else ""

    return settings


@router.put("")
async def update_settings(update: SettingsUpdate, db=Depends(get_db)):
    """Update settings (apiKeys and budget)."""
    # Update budget if provided
    if update.budget is not None:
        if update.budget < 0:
            raise HTTPException(status_code=400, detail="Budget must be non-negative")

        result = await db.execute(select(UserProfile).filter(UserProfile.key == "settings.budget"))
        profile = result.scalar()

        if profile:
            profile.value = {"value": update.budget}
        else:
            profile = UserProfile(key="settings.budget", value={"value": update.budget})
            db.add(profile)

    # Update API keys if provided
    api_key_mapping = {
        "anthropic": "settings.anthropic_key",
        "openai": "settings.openai_key",
        "google": "settings.google_key",
        "ollamaBaseUrl": "settings.ollama_url"
    }

    for key_name, setting_key in api_key_mapping.items():
        if key_name in update.apiKeys:
            value = update.apiKeys[key_name]
            if value:  # Only update if value is provided
                result = await db.execute(select(UserProfile).filter(UserProfile.key == setting_key))
                profile = result.scalar()

                if profile:
                    profile.value = {"value": value}
                else:
                    profile = UserProfile(key=setting_key, value={"value": value})
                    db.add(profile)

    await db.commit()
    return {"status": "ok"}


@router.post("/test-provider/{provider}")
async def test_provider(provider: str, test: ProviderTest):
    """Test API provider connection."""
    try:
        if provider == "anthropic":
            if not test.apiKey:
                return {"status": False}
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.anthropic.com/v1/models",
                    headers={"x-api-key": test.apiKey},
                    timeout=5.0
                )
                return {"status": response.status_code == 200}

        elif provider == "openai":
            if not test.apiKey:
                return {"status": False}
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {test.apiKey}"},
                    timeout=5.0
                )
                return {"status": response.status_code == 200}

        elif provider == "google":
            if not test.apiKey:
                return {"status": False}
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://generativelanguage.googleapis.com/v1/models?key={test.apiKey}",
                    timeout=5.0
                )
                return {"status": response.status_code == 200}

        elif provider == "ollama":
            if not test.baseUrl:
                return {"status": False}
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{test.baseUrl}/api/tags",
                    timeout=5.0
                )
                return {"status": response.status_code == 200}

        else:
            raise HTTPException(status_code=400, detail="Unknown provider")

    except Exception:
        return {"status": False}
