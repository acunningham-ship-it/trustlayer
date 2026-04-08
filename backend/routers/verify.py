"""Verification Engine — trust scores, fact-checking, hallucination detection."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
import re
import hashlib

router = APIRouter()


class VerifyRequest(BaseModel):
    content: str
    context: Optional[str] = None
    check_plagiarism: bool = True
    check_hallucination: bool = True


class TrustScore:
    """Compute a trust score for AI-generated content."""

    def __init__(self, content: str, context: str = None):
        self.content = content
        self.context = context
        self.issues = []
        self.score = 100

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

    def compute(self) -> dict:
        self.check_uncertainty_language()
        self.check_specific_claims()
        self.check_length_quality()
        self.check_repetition()

        final_score = max(0, min(100, self.score))
        return {
            "score": final_score,
            "label": self._label(final_score),
            "issues": self.issues,
            "word_count": len(self.content.split()),
            "content_hash": hashlib.sha256(self.content.encode()).hexdigest()[:16],
        }

    def _label(self, score: int) -> str:
        if score >= 85:
            return "high"
        elif score >= 60:
            return "medium"
        else:
            return "low"


@router.post("/")
async def verify_content(req: VerifyRequest):
    """Run full verification on AI-generated content."""
    scorer = TrustScore(req.content, req.context)
    result = scorer.compute()

    return {
        "trust_score": result["score"],
        "trust_label": result["label"],
        "verified_claims": 0,  # TODO: integrate fact-check API
        "unverified_claims": len(result["issues"]),
        "issues": result["issues"],
        "summary": f"This response is {result['score']}% trusted. {len(result['issues'])} concern(s) flagged.",
        "content_hash": result["content_hash"],
        "word_count": result["word_count"],
    }


@router.post("/batch")
async def verify_batch(items: list[VerifyRequest]):
    """Verify multiple responses (for model comparison)."""
    results = []
    for item in items:
        scorer = TrustScore(item.content, item.context)
        result = scorer.compute()
        results.append(result)
    return results
