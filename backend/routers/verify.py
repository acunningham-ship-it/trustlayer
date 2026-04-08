"""Verification Engine — trust scores, fact-checking, hallucination detection."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List
import re
import hashlib
import json
from urllib.parse import urlparse
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import AIInteraction, get_db

router = APIRouter()


class VerifyRequest(BaseModel):
    content: str
    context: Optional[str] = None
    check_plagiarism: bool = True
    check_hallucination: bool = True


class SourceCitation:
    """Extract and track source citations from content."""

    def __init__(self, content: str):
        self.content = content
        self.citations = []
        self.urls = []
        self._extract()

    def _extract(self):
        """Extract URLs and citation patterns."""
        # Extract URLs
        url_pattern = r'https?://[^\s\)"\]<>]+'
        self.urls = re.findall(url_pattern, self.content)

        # Extract citation patterns like "[1]", "(Smith, 2020)", "According to X"
        citation_patterns = [
            r'\[\d+\]',  # [1] style citations
            r'\([\w\s&,]+,\s*\d{4}\)',  # (Author, Year) style
            r'(?:According to|According to|Per|Via|From|Source:)\s+([^.!?]+)',
        ]

        for pattern in citation_patterns:
            matches = re.findall(pattern, self.content, re.IGNORECASE)
            self.citations.extend(matches)

    def get_summary(self) -> dict:
        return {
            "citation_count": len(self.citations),
            "url_count": len(self.urls),
            "urls": list(set(self.urls)),
            "has_citations": len(self.citations) > 0,
        }


class ClaimExtractor:
    """Extract key claims from content for fact-checking."""

    def __init__(self, content: str):
        self.content = content
        self.claims = []
        self._extract()

    def _extract(self):
        """Extract specific, factual claims."""
        # Patterns for extractable claims
        patterns = [
            r'([\w\s]+)\s+(?:is|are|was|were|has|have|claimed|stated|reported|showed|found)\s+([^.!?]+)',  # Subject + verb + claim
            r'([\d.]+)\s+(%|percent|million|billion|thousand|years?|months?)\s+([^.!?]+)',  # Specific statistics
            r'(on|in|during)\s+([^.!?]+?)\s*[,.]',  # Temporal claims
        ]

        for pattern in patterns:
            matches = re.findall(pattern, self.content, re.IGNORECASE)
            self.claims.extend([match for match in matches if match])

    def get_claims(self) -> List[str]:
        return [' '.join(claim) if isinstance(claim, tuple) else claim for claim in self.claims[:10]]


class TrustScore:
    """Compute a trust score for AI-generated content."""

    def __init__(self, content: str, context: str = None):
        self.content = content
        self.context = context
        self.issues = []
        self.score = 100
        self.sources = SourceCitation(content)
        self.claims = ClaimExtractor(content)

    def check_uncertainty_language(self):
        """Flag missing uncertainty — confident claims with no hedging."""
        confident_patterns = [
            r"\b(always|never|definitely|certainly|guaranteed|100%)\b",
            r"\b(fact is|the truth is|it is proven)\b",
        ]
        uncertain_good = [
            r"\b(may|might|could|likely|approximately|around|suggests)\b",
            r"\b(I think|I believe|as far as I know|to my knowledge)\b",
        ]

        confident_count = sum(
            len(re.findall(p, self.content, re.IGNORECASE))
            for p in confident_patterns
        )
        uncertain_count = sum(
            len(re.findall(p, self.content, re.IGNORECASE))
            for p in uncertain_good
        )

        if confident_count > 3 and uncertain_count == 0:
            self.score -= 15
            self.issues.append("High confidence language with no hedging — may be overconfident")

    def check_specific_claims(self):
        """Flag very specific numbers/dates/names that could be hallucinated."""
        # Specific stats/percentages
        stats = re.findall(r"\d+\.?\d*%", self.content)
        specific_years = re.findall(r"\b(19|20)\d{2}\b", self.content)

        if len(stats) > 5:
            self.score -= 10
            self.issues.append(f"Contains {len(stats)} specific statistics — verify independently")

        if len(specific_years) > 3:
            self.score -= 5
            self.issues.append(f"Contains {len(specific_years)} specific dates — double-check accuracy")

    def check_length_quality(self):
        """Very short responses to complex questions are suspicious."""
        word_count = len(self.content.split())
        if self.context and len(self.context.split()) > 20 and word_count < 10:
            self.score -= 20
            self.issues.append("Response is unusually short for the question complexity")

    def check_repetition(self):
        """Repetitive content often indicates low-quality generation."""
        sentences = re.split(r'[.!?]+', self.content)
        unique = set(s.strip().lower() for s in sentences if len(s.strip()) > 10)
        if len(sentences) > 3 and len(unique) < len(sentences) * 0.6:
            self.score -= 15
            self.issues.append("Content has significant repetition")

    def check_factual_consistency(self):
        """Check for contradictions within the content."""
        sentences = [s.strip() for s in re.split(r'[.!?]+', self.content) if s.strip()]

        # Check for contradictory words in close proximity
        contradictions = [
            (r'\b(but|however|yet|although)\b.*\b(same|identical|exactly the same)\b', 'Logical contradiction detected'),
            (r'\b(true|false|yes|no)\s*[,;]\s*(?!true|yes)\b(false|no)\b', 'Direct contradiction'),
            (r'\bwill\s+.*\b(cannot|will not)\b', 'Future state contradiction'),
        ]

        for pattern, issue in contradictions:
            if re.search(pattern, self.content, re.IGNORECASE):
                self.score -= 8
                self.issues.append(issue)

    def check_source_citations(self):
        """Reward content with proper source citations."""
        source_info = self.sources.get_summary()

        if source_info["citation_count"] == 0 and source_info["url_count"] == 0:
            # No sources cited - flag as potential hallucination
            if len(self.content.split()) > 50:  # Only penalize longer content
                self.score -= 10
                self.issues.append("Long response with no cited sources — verify claims independently")
        else:
            # Has sources - positive signal
            self.score = min(100, self.score + 5)

    def check_specific_entities(self):
        """Detect hallucinated names, places, dates."""
        # Extract proper nouns (capitalized words)
        proper_nouns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', self.content)

        # Check for suspiciously formatted or unusual patterns
        suspicious_patterns = [
            r'\b[A-Z]{2,}\s+[0-9]{2,}\b',  # ALL CAPS followed by numbers
            r'\b[A-Z][a-z]+shire\b',  # Fantasy location names
            r'\bJohn\s+(?:Smith|Doe|Johnson)\b',  # Generic names
        ]

        suspicious_count = sum(
            len(re.findall(p, self.content, re.IGNORECASE))
            for p in suspicious_patterns
        )

        if suspicious_count > 2:
            self.score -= 12
            self.issues.append("Content contains potentially fabricated names or locations")

    def compute(self) -> dict:
        self.check_uncertainty_language()
        self.check_specific_claims()
        self.check_length_quality()
        self.check_repetition()
        self.check_factual_consistency()
        self.check_source_citations()
        self.check_specific_entities()

        final_score = max(0, min(100, self.score))
        return {
            "score": final_score,
            "label": self._label(final_score),
            "issues": self.issues,
            "word_count": len(self.content.split()),
            "content_hash": hashlib.sha256(self.content.encode()).hexdigest()[:16],
            "claims": self.claims.get_claims(),
            "sources": self.sources.get_summary(),
        }

    def _label(self, score: int) -> str:
        if score >= 85:
            return "high"
        elif score >= 60:
            return "medium"
        else:
            return "low"


@router.post("/")
async def verify_content(req: VerifyRequest, db: AsyncSession = Depends(get_db)):
    """Run full verification on AI-generated content."""
    scorer = TrustScore(req.content, req.context)
    result = scorer.compute()

    # Record AIInteraction for analytics
    interaction = AIInteraction(
        provider="trustlayer",
        model="verify",
        prompt=req.content,
        response=json.dumps(result),
        trust_score=result["score"],
        tokens_used=result["word_count"],
        cost_usd=0.0,
    )
    db.add(interaction)
    await db.commit()

    claims = result.get("claims", [])
    sources = result.get("sources", {})

    return {
        "trust_score": result["score"],
        "trust_label": result["label"],
        "verified_claims": sources.get("citation_count", 0),
        "unverified_claims": len(result["issues"]),
        "issues": result["issues"],
        "summary": f"This response is {result['score']}% trusted. {len(result['issues'])} concern(s) flagged. {sources.get('citation_count', 0)} source(s) cited.",
        "content_hash": result["content_hash"],
        "word_count": result["word_count"],
        "extracted_claims": claims,
        "sources": {
            "urls": sources.get("urls", []),
            "citation_count": sources.get("citation_count", 0),
            "has_proper_citations": sources.get("has_citations", False),
        },
        "hallucination_score": 100 - result["score"],  # Inverse: higher score = more hallucination risk
    }


@router.post("/batch")
async def verify_batch(items: list[VerifyRequest], db: AsyncSession = Depends(get_db)):
    """Verify multiple responses (for model comparison)."""
    results = []
    for item in items:
        scorer = TrustScore(item.content, item.context)
        result = scorer.compute()

        # Record AIInteraction for analytics
        interaction = AIInteraction(
            provider="trustlayer",
            model="verify",
            prompt=item.content,
            response=json.dumps(result),
            trust_score=result["score"],
            tokens_used=result["word_count"],
            cost_usd=0.0,
        )
        db.add(interaction)
        results.append(result)

    await db.commit()
    return results
