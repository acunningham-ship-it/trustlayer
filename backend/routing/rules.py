"""Routing rules — define when to re-route requests to cheaper models."""

from pydantic import BaseModel
from sqlalchemy import select

from ..database import AsyncSessionLocal, UserProfile


class RoutingRule(BaseModel):
    """A single routing rule."""
    name: str
    task_types: list[str]           # e.g. ["quick", "factual"]
    model_pattern: str              # regex matched against requested model
    route_to_model: str             # target model (cloud)
    requires_ollama: bool = False   # if True, route to local Ollama instead
    ollama_model: str | None = None # which Ollama model to use
    enabled: bool = True
    priority: int = 100             # lower = higher priority


DEFAULT_RULES: list[RoutingRule] = [
    RoutingRule(
        name="gpt4o-quick-to-mini",
        task_types=["quick", "factual"],
        model_pattern=r"^gpt-4o$",
        route_to_model="gpt-4o-mini",
        priority=10,
    ),
    RoutingRule(
        name="gpt4-turbo-quick-to-mini",
        task_types=["quick", "factual"],
        model_pattern=r"^gpt-4-turbo",
        route_to_model="gpt-4o-mini",
        priority=15,
    ),
    RoutingRule(
        name="claude-opus-quick-to-haiku",
        task_types=["quick"],
        model_pattern=r"^claude-opus",
        route_to_model="claude-haiku-3-20240307",
        priority=10,
    ),
    RoutingRule(
        name="cloud-factual-to-ollama",
        task_types=["factual"],
        model_pattern=r"^(gpt-|claude-|gemini-)",
        route_to_model="ollama",
        requires_ollama=True,
        ollama_model="llama3.2",
        priority=50,
    ),
]

SETTINGS_KEY = "settings.routing_rules"


async def load_rules() -> list[RoutingRule]:
    """Load custom routing rules from DB, falling back to defaults."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(UserProfile).filter(UserProfile.key == SETTINGS_KEY)
            )
            row = result.scalar()
            if row and isinstance(row.value, list):
                return [RoutingRule(**r) for r in row.value]
    except Exception:
        pass
    return list(DEFAULT_RULES)


async def save_rules(rules: list[RoutingRule]) -> None:
    """Persist routing rules to the user_profiles table."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserProfile).filter(UserProfile.key == SETTINGS_KEY)
        )
        row = result.scalar()
        data = [r.model_dump() for r in rules]

        if row:
            row.value = data
        else:
            row = UserProfile(key=SETTINGS_KEY, value=data)
            session.add(row)

        await session.commit()
