"""Settings router — runtime configuration management."""

import httpx
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from ..database import get_db, UserProfile, ProxyLog
from ..routing.rules import RoutingRule, DEFAULT_RULES, load_rules, save_rules
from ..providers.registry import rebuild_registry

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


def _mask_key(key: str) -> str:
    """Mask an API key for display — show first 8 chars then ****."""
    if not key:
        return ""
    visible = min(8, len(key) // 2)
    return key[:visible] + "****"


@router.get("")
async def get_settings(db=Depends(get_db)):
    """Get current configuration settings (apiKeys masked and budget)."""
    settings: dict = {
        "apiKeys": {
            "anthropic": "",
            "openai": "",
            "google": "",
            "ollamaBaseUrl": ""
        },
        "configured": {
            "anthropic": False,
            "openai": False,
            "google": False,
            "ollama": False,
        },
        "budget": None,
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
            raw = value.get("value", "") if isinstance(value, dict) else ""
            settings["apiKeys"]["anthropic"] = _mask_key(raw)
            settings["configured"]["anthropic"] = bool(raw)
        elif setting_name == "openai_key":
            raw = value.get("value", "") if isinstance(value, dict) else ""
            settings["apiKeys"]["openai"] = _mask_key(raw)
            settings["configured"]["openai"] = bool(raw)
        elif setting_name == "google_key":
            raw = value.get("value", "") if isinstance(value, dict) else ""
            settings["apiKeys"]["google"] = _mask_key(raw)
            settings["configured"]["google"] = bool(raw)
        elif setting_name == "ollama_url":
            raw = value.get("value", "") if isinstance(value, dict) else ""
            settings["apiKeys"]["ollamaBaseUrl"] = raw  # URL is not sensitive
            settings["configured"]["ollama"] = bool(raw)

    # Auto-detect Ollama if not explicitly configured
    if not settings["configured"]["ollama"]:
        try:
            import httpx
            r = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
            if r.status_code == 200:
                settings["configured"]["ollama"] = True
                settings["apiKeys"]["ollamaBaseUrl"] = "http://localhost:11434"
        except Exception:
            pass

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

    # Rebuild provider registry with all current keys from DB
    all_keys: dict = {}
    result2 = await db.execute(select(UserProfile).filter(UserProfile.key.startswith("settings.")))
    for row in result2.scalars().all():
        name = row.key.replace("settings.", "")
        val = row.value.get("value", "") if isinstance(row.value, dict) else ""
        all_keys[name] = val

    rebuild_registry(
        anthropic_key=all_keys.get("anthropic_key", ""),
        openai_key=all_keys.get("openai_key", ""),
        google_key=all_keys.get("google_key", ""),
        ollama_url=all_keys.get("ollama_url", ""),
    )

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


@router.post("/test-all")
async def test_all_providers(db=Depends(get_db)):
    """Test all configured providers in parallel."""
    from datetime import datetime, timezone

    # Get all configured settings from database
    try:
        result = await db.execute(select(UserProfile).filter(UserProfile.key.startswith("settings.")))
        settings_rows = result.scalars().all()
    except Exception:
        # Database tables don't exist yet, use empty settings
        settings_rows = []

    settings_dict = {}
    for row in settings_rows:
        setting_name = row.key.replace("settings.", "")
        value = row.value.get("value", "") if isinstance(row.value, dict) else ""
        settings_dict[setting_name] = value

    # Helper to test a provider safely
    async def test_with_error_handling(provider_name: str, test_input: ProviderTest):
        try:
            result = await test_provider(provider_name, test_input)
            return (provider_name, result)
        except Exception as e:
            return (provider_name, {"status": False, "error": str(e)})

    # Create test tasks for each provider
    tasks = [
        test_with_error_handling("anthropic", ProviderTest(apiKey=settings_dict.get("anthropic_key", ""))),
        test_with_error_handling("openai", ProviderTest(apiKey=settings_dict.get("openai_key", ""))),
        test_with_error_handling("google", ProviderTest(apiKey=settings_dict.get("google_key", ""))),
        test_with_error_handling("ollama", ProviderTest(baseUrl=settings_dict.get("ollama_url", "http://localhost:11434"))),
    ]

    # Run all tests in parallel
    try:
        test_results = await asyncio.gather(*tasks)

        # Build results dict
        results = {}
        for provider_name, test_result in test_results:
            results[provider_name] = {
                "configured": bool(
                    settings_dict.get(f"{provider_name}_key")
                    if provider_name != "ollama"
                    else settings_dict.get("ollama_url")
                ),
                "status": test_result.get("status", False),
                **test_result,
            }

        # Count passing tests
        passing = sum(1 for r in results.values() if r.get("status", False))

        return {
            "tested_at": datetime.now(timezone.utc).isoformat(),
            "total_providers": len(results),
            "passing": passing,
            "failing": len(results) - passing,
            "results": results,
        }

    except Exception as e:
        return {
            "error": str(e),
            "tested_at": datetime.now(timezone.utc).isoformat(),
        }



# ---------------------------------------------------------------------------
# Routing settings
# ---------------------------------------------------------------------------

class RoutingRulesUpdate(BaseModel):
    rules: list[RoutingRule]


@router.get("/routing")
async def get_routing_rules():
    """Return current routing rules."""
    rules = await load_rules()
    return {
        "rules": [r.model_dump() for r in rules],
        "count": len(rules),
    }


@router.put("/routing")
async def update_routing_rules(update: RoutingRulesUpdate):
    """Update routing rules."""
    await save_rules(update.rules)
    return {"status": "ok", "count": len(update.rules)}


@router.post("/routing/reset")
async def reset_routing_rules():
    """Reset routing rules to defaults."""
    await save_rules(DEFAULT_RULES)
    return {"status": "ok", "count": len(DEFAULT_RULES)}


@router.get("/routing/stats")
async def get_routing_stats(db=Depends(get_db)):
    """Return routing statistics — total routed requests and savings."""
    from sqlalchemy import func

    # Total routed requests
    result = await db.execute(
        select(
            func.count(ProxyLog.id).label("total_routed"),
            func.coalesce(func.sum(ProxyLog.savings_usd), 0.0).label("total_savings"),
        ).filter(ProxyLog.routed_from.isnot(None))
    )
    row = result.one()

    # Total requests overall
    total_result = await db.execute(select(func.count(ProxyLog.id)))
    total_requests = total_result.scalar() or 0

    return {
        "total_requests": total_requests,
        "total_routed": row.total_routed,
        "total_savings_usd": round(float(row.total_savings), 6),
        "routing_rate_pct": round(row.total_routed / total_requests * 100, 1) if total_requests > 0 else 0.0,
    }
