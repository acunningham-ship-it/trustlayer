"""Smart routing engine — classifies prompts and routes to cheaper models."""

import re
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx

from .rules import DEFAULT_RULES, RoutingRule

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Task classification keywords
# ---------------------------------------------------------------------------

TASK_PATTERNS: dict[str, list[str]] = {
    "quick": [
        r"\b(hi|hello|hey|thanks|ok|yes|no|sure)\b",
        r"^.{0,30}$",  # Very short prompts
        r"\bwhat is \d+\s*[\+\-\*\/]\s*\d+",
        r"\b(translate|convert)\b.*\b(to|into)\b",
    ],
    "factual": [
        r"\b(what|who|when|where|which|how many|how much|define|meaning of)\b",
        r"\b(capital of|population of|distance between)\b",
        r"\b(list|name|enumerate)\b.*\b(the|all|some)\b",
        r"\b(fact|true|false|correct)\b",
    ],
    "code": [
        r"\b(code|function|class|def |import |from |return |async |await )\b",
        r"\b(write|implement|debug|fix|refactor|optimize)\b.*\b(code|function|script|program|bug)\b",
        r"\b(python|javascript|typescript|rust|go|java|c\+\+|html|css|sql)\b",
        r"```",
    ],
    "creative": [
        r"\b(write|create|compose|draft|generate)\b.*\b(story|poem|essay|song|article|blog)\b",
        r"\b(creative|imagine|fiction|narrative)\b",
        r"\b(brainstorm|ideas? for)\b",
    ],
    "analysis": [
        r"\b(analyze|analyse|evaluate|compare|contrast|assess|review)\b",
        r"\b(explain|why|reason|cause|implications?|consequences?)\b.*\b(in detail|thoroughly|deeply)\b",
        r"\b(pros? and cons?|trade-?offs?|advantages? and disadvantages?)\b",
        r"\b(strategy|architecture|design|plan)\b.*\b(for|to)\b",
    ],
}

# Pre-compile all patterns
COMPILED_PATTERNS: dict[str, list[re.Pattern]] = {
    task: [re.compile(p, re.IGNORECASE) for p in patterns]
    for task, patterns in TASK_PATTERNS.items()
}

# Approximate per-token costs (USD per 1M tokens, input) for savings estimation
MODEL_COSTS: dict[str, float] = {
    "gpt-4o": 2.50,
    "gpt-4o-mini": 0.15,
    "gpt-4-turbo": 10.00,
    "claude-opus-4-20250514": 15.00,
    "claude-sonnet-4-20250514": 3.00,
    "claude-haiku-3-20240307": 0.25,
}


@dataclass
class RoutingDecision:
    """Result of the routing engine evaluation."""
    original_model: str
    routed_model: str
    reason: str
    estimated_savings_pct: float = 0.0
    estimated_savings_usd: float = 0.0
    task_type: str = "unknown"
    was_routed: bool = False


class RoutingEngine:
    """Classify prompts and route to cheaper models when appropriate."""

    _ollama_available: Optional[bool] = None
    _ollama_checked_at: float = 0.0
    OLLAMA_CHECK_TTL: float = 30.0  # seconds

    def __init__(self, rules: list[RoutingRule] | None = None, ollama_url: str = "http://localhost:11434"):
        self.rules = rules if rules is not None else DEFAULT_RULES
        self.ollama_url = ollama_url

    def classify(self, messages: list[dict]) -> str:
        """Classify a conversation into a task type based on the last user message."""
        last_user_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    last_user_msg = content
                elif isinstance(content, list):
                    last_user_msg = " ".join(
                        p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"
                    )
                break

        if not last_user_msg:
            return "unknown"

        scores: dict[str, int] = {}
        for task_type, patterns in COMPILED_PATTERNS.items():
            for pattern in patterns:
                if pattern.search(last_user_msg):
                    scores[task_type] = scores.get(task_type, 0) + 1

        if not scores:
            return "unknown"

        return max(scores, key=scores.get)

    async def check_ollama(self) -> bool:
        """Check if Ollama is reachable (cached for OLLAMA_CHECK_TTL seconds)."""
        now = time.time()
        if self._ollama_available is not None and (now - self._ollama_checked_at) < self.OLLAMA_CHECK_TTL:
            return self._ollama_available

        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                r = await client.get(f"{self.ollama_url}/api/tags")
                RoutingEngine._ollama_available = r.status_code == 200
        except Exception:
            RoutingEngine._ollama_available = False

        RoutingEngine._ollama_checked_at = now
        return RoutingEngine._ollama_available

    async def evaluate(self, model: str, messages: list[dict]) -> RoutingDecision:
        """Evaluate whether a request should be routed to a cheaper model."""
        task_type = self.classify(messages)

        # If model is already local Ollama, no routing needed
        model_lower = model.lower()
        is_local = not any(
            model_lower.startswith(p)
            for p in ("gpt-", "claude-", "gemini-", "openai/", "anthropic/", "google/")
        )
        if is_local:
            return RoutingDecision(
                original_model=model,
                routed_model=model,
                reason="Already a local model",
                task_type=task_type,
            )

        # Check each rule in priority order
        sorted_rules = sorted(
            [r for r in self.rules if r.enabled],
            key=lambda r: r.priority,
        )

        for rule in sorted_rules:
            if task_type not in rule.task_types:
                continue
            if not re.search(rule.model_pattern, model, re.IGNORECASE):
                continue

            target_model = rule.route_to_model

            # If routing to Ollama, verify availability
            if rule.requires_ollama:
                if not await self.check_ollama():
                    continue
                target_model = rule.ollama_model or "llama3.2"

            # Calculate savings estimate
            orig_cost = MODEL_COSTS.get(model, 5.0)
            target_cost = MODEL_COSTS.get(target_model, 0.0)
            savings_pct = max(0.0, (orig_cost - target_cost) / orig_cost * 100) if orig_cost > 0 else 0.0
            # Rough per-request savings (assume ~1K tokens)
            savings_usd = (orig_cost - target_cost) / 1_000_000 * 1000

            return RoutingDecision(
                original_model=model,
                routed_model=target_model,
                reason=f"Rule {rule.name}: {task_type} task routed from {model} to {target_model}",
                estimated_savings_pct=round(savings_pct, 1),
                estimated_savings_usd=round(max(0.0, savings_usd), 6),
                task_type=task_type,
                was_routed=True,
            )

        return RoutingDecision(
            original_model=model,
            routed_model=model,
            reason=f"No routing rule matched for task_type={task_type}",
            task_type=task_type,
        )
