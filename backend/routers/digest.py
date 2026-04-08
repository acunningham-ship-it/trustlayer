"""Digest router — savings tracking and daily/weekly summaries."""

from datetime import datetime, timedelta, UTC
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db

router = APIRouter()

# Claude Sonnet pricing per 1M tokens (used as baseline for Ollama savings)
SONNET_INPUT_PER_M = 3.0
SONNET_OUTPUT_PER_M = 15.0

# Try importing PRICING from openai_compat for routing savings
try:
    from ..providers.openai_compat import PRICING
except ImportError:
    PRICING = {}


def _estimate_cloud_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate what Ollama tokens would cost on Claude Sonnet."""
    return (prompt_tokens * SONNET_INPUT_PER_M + completion_tokens * SONNET_OUTPUT_PER_M) / 1_000_000


def _model_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate cost for a specific model using PRICING dict."""
    price_in, price_out = PRICING.get(model, (0, 0))
    return (prompt_tokens * price_in + completion_tokens * price_out) / 1_000_000


async def _compute_digest(db: AsyncSession, since: datetime) -> dict:
    """Compute digest stats from proxy_logs since a given datetime."""
    since_str = since.strftime("%Y-%m-%d %H:%M:%S")

    # Basic stats
    base_query = text("""
        SELECT
            COUNT(*) as total_requests,
            COALESCE(SUM(prompt_tokens), 0) as total_prompt_tokens,
            COALESCE(SUM(completion_tokens), 0) as total_completion_tokens,
            COALESCE(SUM(cost_usd), 0) as total_cost
        FROM proxy_logs
        WHERE timestamp >= :since
    """)
    result = await db.execute(base_query, {"since": since_str})
    row = result.fetchone()

    total_requests = row[0] if row else 0
    total_prompt_tokens = row[1] if row else 0
    total_completion_tokens = row[2] if row else 0
    total_cost = row[3] if row else 0.0

    # Top models
    models_query = text("""
        SELECT model, COUNT(*) as cnt, COALESCE(SUM(cost_usd), 0) as cost
        FROM proxy_logs
        WHERE timestamp >= :since
        GROUP BY model
        ORDER BY cnt DESC
        LIMIT 5
    """)
    result = await db.execute(models_query, {"since": since_str})
    top_models = [
        {"model": r[0], "requests": r[1], "cost_usd": round(r[2], 6)}
        for r in result.fetchall()
    ]

    # Ollama savings: all requests where provider = 'ollama'
    ollama_query = text("""
        SELECT
            COALESCE(SUM(prompt_tokens), 0),
            COALESCE(SUM(completion_tokens), 0)
        FROM proxy_logs
        WHERE timestamp >= :since AND provider = 'ollama'
    """)
    result = await db.execute(ollama_query, {"since": since_str})
    ollama_row = result.fetchone()
    ollama_savings = 0.0
    if ollama_row:
        ollama_savings = _estimate_cloud_cost(ollama_row[0], ollama_row[1])

    # Routing savings: check if routed_from column exists
    routing_decisions = 0
    routing_savings = 0.0
    try:
        routed_query = text("""
            SELECT model, routed_from, prompt_tokens, completion_tokens, cost_usd
            FROM proxy_logs
            WHERE timestamp >= :since AND routed_from IS NOT NULL AND routed_from != ''
        """)
        result = await db.execute(routed_query, {"since": since_str})
        routed_rows = result.fetchall()
        routing_decisions = len(routed_rows)
        for r in routed_rows:
            actual_model, original_model, pt, ct, actual_cost = r
            original_cost = _model_cost(original_model, pt, ct)
            if original_cost > actual_cost:
                routing_savings += original_cost - actual_cost
    except Exception:
        routing_decisions = 0
        routing_savings = 0.0

    # Also check for savings_usd column
    explicit_savings = 0.0
    try:
        savings_query = text("""
            SELECT COALESCE(SUM(savings_usd), 0)
            FROM proxy_logs
            WHERE timestamp >= :since AND savings_usd > 0
        """)
        result = await db.execute(savings_query, {"since": since_str})
        srow = result.fetchone()
        if srow:
            explicit_savings = srow[0]
    except Exception:
        explicit_savings = 0.0

    total_savings = ollama_savings + routing_savings + explicit_savings
    total_tokens = total_prompt_tokens + total_completion_tokens

    # Daily breakdown for the period
    daily_query = text("""
        SELECT
            DATE(timestamp) as day,
            COUNT(*) as requests,
            COALESCE(SUM(cost_usd), 0) as cost
        FROM proxy_logs
        WHERE timestamp >= :since
        GROUP BY DATE(timestamp)
        ORDER BY day
    """)
    result = await db.execute(daily_query, {"since": since_str})
    daily_breakdown = [
        {"date": str(r[0]), "requests": r[1], "cost_usd": round(r[2], 6)}
        for r in result.fetchall()
    ]

    return {
        "savings_usd": round(total_savings, 4),
        "ollama_savings_usd": round(ollama_savings, 4),
        "routing_savings_usd": round(routing_savings + explicit_savings, 4),
        "requests_count": total_requests,
        "tokens_total": total_tokens,
        "total_cost_usd": round(total_cost, 6),
        "top_models": top_models,
        "routing_decisions": routing_decisions,
        "daily_breakdown": daily_breakdown,
    }


@router.get("/daily")
async def daily_digest(db: AsyncSession = Depends(get_db)):
    """Get today's usage stats and savings."""
    since = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return await _compute_digest(db, since)


@router.get("/weekly")
async def weekly_digest(db: AsyncSession = Depends(get_db)):
    """Get the last 7 days of usage stats and savings."""
    since = datetime.now(UTC) - timedelta(days=7)
    return await _compute_digest(db, since)
