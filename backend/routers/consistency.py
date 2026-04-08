"""Response Consistency Tracker — detect hallucinations via multi-run consistency analysis."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import json
import re
from difflib import SequenceMatcher
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import AIInteraction, get_db
from ..providers.registry import get_registry

router = APIRouter()


class ConsistencyRequest(BaseModel):
    """Request to run consistency check on a prompt."""
    prompt: str
    provider: str
    model: str
    runs: int = 3
    max_tokens: Optional[int] = 1024


class ConsistencyResult(BaseModel):
    """Result of consistency analysis."""
    consistency_score: float  # 0-100, higher = more consistent
    responses: List[str]
    common_claims: List[str]
    disputed_claims: List[str]
    summary: str


def extract_sentences(text: str) -> List[str]:
    """Extract sentences from text, cleaning up whitespace."""
    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    # Filter out very short sentences and empty ones
    sentences = [
        s.strip() for s in sentences
        if len(s.strip()) > 10 and s.strip()
    ]
    return sentences


def extract_claims(text: str) -> List[str]:
    """Extract factual claims from text (sentences with specific details)."""
    sentences = extract_sentences(text)
    claims = []

    for sentence in sentences:
        # Look for sentences with specific facts (numbers, names, dates, etc.)
        # or definitive statements
        if (
            re.search(r'\b\d+\b', sentence)  # Contains numbers
            or re.search(r'\b(January|February|March|April|May|June|July|August|September|October|November|December|20\d{2})\b', sentence, re.IGNORECASE)
            or re.search(r'\b(was|were|is|are|said|reported|found|showed)\b', sentence, re.IGNORECASE)
        ):
            claims.append(sentence)

    return claims[:20]  # Limit to top 20 claims


def normalize_claim(claim: str) -> str:
    """Normalize a claim for comparison (lowercase, remove punctuation, etc.)."""
    # Remove extra whitespace
    normalized = ' '.join(claim.split())
    # Remove trailing punctuation
    normalized = normalized.rstrip('.!?,;:')
    # Convert to lowercase
    normalized = normalized.lower()
    return normalized


def string_similarity(a: str, b: str) -> float:
    """Calculate similarity between two strings (0-1)."""
    return SequenceMatcher(None, a, b).ratio()


def cluster_similar_claims(claims: List[str], threshold: float = 0.75) -> dict:
    """Cluster similar claims together.

    Returns:
        {
            'common': [list of claims found in multiple responses],
            'disputed': [list of claims found in some but not all],
            'appearances': {claim: count of how many times it appeared}
        }
    """
    if not claims:
        return {
            "common": [],
            "disputed": [],
            "appearances": {},
        }

    normalized = [normalize_claim(c) for c in claims]
    clusters = {}  # Map normalized -> original claims
    appearances = {}  # Count of each normalized claim

    for original, norm in zip(claims, normalized):
        # Find if this claim is similar to existing clusters
        found_cluster = None

        for existing_norm, existing_originals in clusters.items():
            similarity = string_similarity(norm, existing_norm)
            if similarity >= threshold:
                found_cluster = existing_norm
                break

        if found_cluster:
            clusters[found_cluster].append(original)
            appearances[found_cluster] += 1
        else:
            clusters[norm] = [original]
            appearances[norm] = 1

    # Categorize claims
    total_runs = max(appearances.values()) if appearances else 1
    common = []
    disputed = []

    for norm, count in appearances.items():
        representative = clusters[norm][0]  # Use first occurrence as representative
        if count == total_runs:
            common.append(representative)
        elif count > 1:
            disputed.append(f"{representative} ({count}/{total_runs} runs agreed)")
        # Single mentions not included

    return {
        "common": common,
        "disputed": disputed,
        "appearances": {k: v for k, v in appearances.items()},
        "cluster_count": len(clusters),
    }


@router.post("/check")
async def consistency_check(
    req: ConsistencyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run the same prompt multiple times and check response consistency."""
    if req.runs < 2:
        return {
            "error": "Must run at least 2 times to measure consistency",
            "consistency_score": None,
        }

    registry = get_registry()
    provider = registry.get(req.provider)

    if not provider:
        return {
            "error": f"Provider {req.provider} not available",
            "consistency_score": None,
        }

    # Run the prompt N times in parallel
    async def run_once():
        try:
            response = await provider.complete(
                req.prompt, req.model, max_tokens=req.max_tokens
            )
            return response.content
        except Exception as e:
            return f"[ERROR: {str(e)}]"

    # Execute all runs in parallel
    tasks = [run_once() for _ in range(req.runs)]
    responses = await asyncio.gather(*tasks)

    # Filter out error responses
    valid_responses = [r for r in responses if not r.startswith("[ERROR")]
    if not valid_responses:
        return {
            "error": "All runs failed",
            "consistency_score": 0.0,
            "responses": responses,
        }

    # Extract claims from all responses
    all_claims = []
    for response in valid_responses:
        claims = extract_claims(response)
        all_claims.extend(claims)

    # Cluster claims to find common vs disputed
    clustering = cluster_similar_claims(all_claims, threshold=0.75)
    common_claims = clustering["common"]
    disputed_claims = clustering["disputed"]

    # Calculate consistency score
    # consistency = (common claims / total unique claims) * 100
    total_unique = len(common_claims) + len(disputed_claims)
    if total_unique > 0:
        consistency_score = (len(common_claims) / total_unique) * 100
    else:
        consistency_score = 100.0 if not all_claims else 0.0

    consistency_score = max(0, min(100, consistency_score))

    # Build summary
    summary_parts = [
        f"Ran prompt {len(valid_responses)} times.",
    ]

    if common_claims:
        summary_parts.append(
            f"{len(common_claims)} claims appeared in all runs (highly reliable)."
        )

    if disputed_claims:
        summary_parts.append(
            f"{len(disputed_claims)} claims appeared in only some runs (potentially hallucinated)."
        )

    if consistency_score >= 80:
        summary_parts.append("Overall: Very consistent responses — high confidence.")
    elif consistency_score >= 60:
        summary_parts.append("Overall: Mostly consistent responses — generally reliable.")
    elif consistency_score >= 40:
        summary_parts.append("Overall: Inconsistent responses — caution advised.")
    else:
        summary_parts.append("Overall: Highly inconsistent — likely hallucinations detected.")

    summary = " ".join(summary_parts)

    # Record interactions in database
    for response in valid_responses:
        interaction = AIInteraction(
            provider=req.provider,
            model=req.model,
            prompt=req.prompt,
            response=response,
            trust_score=consistency_score,  # Use consistency as proxy for trust
            tokens_used=0,  # Could parse from response
            cost_usd=0.0,
        )
        db.add(interaction)

    await db.commit()

    return {
        "consistency_score": round(consistency_score, 1),
        "consistency_label": (
            "high" if consistency_score >= 80
            else "medium" if consistency_score >= 60
            else "low" if consistency_score >= 40
            else "very_low"
        ),
        "runs_completed": len(valid_responses),
        "responses": valid_responses,
        "common_claims": common_claims,
        "disputed_claims": disputed_claims,
        "summary": summary,
        "analysis": {
            "total_unique_claims": total_unique,
            "common_claim_count": len(common_claims),
            "disputed_claim_count": len(disputed_claims),
            "agreement_percentage": round(
                (len(common_claims) / total_unique * 100) if total_unique > 0 else 100,
                1
            ),
        },
    }


@router.post("/compare-responses")
async def compare_responses(
    responses: List[str],
    db: AsyncSession = Depends(get_db),
):
    """Compare pre-generated responses for consistency without re-running."""
    if len(responses) < 2:
        return {
            "error": "Need at least 2 responses to compare",
        }

    # Extract claims from all responses
    all_claims = []
    for response in responses:
        claims = extract_claims(response)
        all_claims.extend(claims)

    # Cluster claims
    clustering = cluster_similar_claims(all_claims, threshold=0.75)
    common_claims = clustering["common"]
    disputed_claims = clustering["disputed"]

    # Calculate consistency score
    total_unique = len(common_claims) + len(disputed_claims)
    if total_unique > 0:
        consistency_score = (len(common_claims) / total_unique) * 100
    else:
        consistency_score = 100.0 if not all_claims else 0.0

    consistency_score = max(0, min(100, consistency_score))

    # Build summary
    summary_parts = [
        f"Compared {len(responses)} responses.",
    ]

    if common_claims:
        summary_parts.append(
            f"{len(common_claims)} claims appeared in all responses."
        )

    if disputed_claims:
        summary_parts.append(
            f"{len(disputed_claims)} claims appeared in only some responses."
        )

    if consistency_score >= 80:
        summary_parts.append("Overall: Very consistent — reliable information.")
    elif consistency_score >= 60:
        summary_parts.append("Overall: Mostly consistent — generally reliable.")
    elif consistency_score >= 40:
        summary_parts.append("Overall: Inconsistent — verify before trusting.")
    else:
        summary_parts.append("Overall: Highly inconsistent — high hallucination risk.")

    return {
        "consistency_score": round(consistency_score, 1),
        "consistency_label": (
            "high" if consistency_score >= 80
            else "medium" if consistency_score >= 60
            else "low" if consistency_score >= 40
            else "very_low"
        ),
        "responses_compared": len(responses),
        "common_claims": common_claims,
        "disputed_claims": disputed_claims,
        "summary": " ".join(summary_parts),
        "analysis": {
            "total_unique_claims": total_unique,
            "common_claim_count": len(common_claims),
            "disputed_claim_count": len(disputed_claims),
            "agreement_percentage": round(
                (len(common_claims) / total_unique * 100) if total_unique > 0 else 100,
                1
            ),
        },
    }


@router.get("/insights")
async def consistency_insights(db: AsyncSession = Depends(get_db)):
    """Get insights about consistency patterns across all models."""
    from sqlalchemy import select, func

    # Get average trust scores (used as consistency proxy) by model
    result = await db.execute(
        select(
            AIInteraction.provider,
            AIInteraction.model,
            func.count().label("count"),
            func.avg(AIInteraction.trust_score).label("avg_consistency"),
        )
        .group_by(AIInteraction.provider, AIInteraction.model)
        .order_by(func.avg(AIInteraction.trust_score).desc())
    )
    rows = result.all()

    if not rows:
        return {
            "total_checks": 0,
            "insights": "No consistency checks recorded yet.",
            "most_consistent_model": None,
            "least_consistent_model": None,
        }

    models = [
        {
            "provider": row[0],
            "model": row[1],
            "consistency_score": round(row[3], 1) if row[3] else 0,
            "checks_run": row[2],
        }
        for row in rows
    ]

    most_consistent = models[0] if models else None
    least_consistent = models[-1] if models else None

    return {
        "total_checks": sum(m["checks_run"] for m in models),
        "models_tested": len(models),
        "most_consistent_model": most_consistent,
        "least_consistent_model": least_consistent,
        "all_models": models,
        "insights": f"{most_consistent['model']} shows the highest consistency score ({most_consistent['consistency_score']}%) across your tests." if most_consistent else "No data yet.",
    }
