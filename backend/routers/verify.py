"""Verification Engine — trust scores, fact-checking, hallucination detection."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List
import re
import hashlib
import json
from urllib.parse import urlparse
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

from ..database import AIInteraction, get_db
from ..providers.registry import get_registry

router = APIRouter()


async def perform_ai_cross_check(claims: List[str], context: str = None) -> dict:
    """
    Ask an available AI provider to fact-check suspicious claims.
    Returns dict with status, ai_assessment, score_adjustment, and provider used.
    """
    if not claims:
        return {"status": "skipped", "reason": "no claims to check"}

    registry = get_registry()
    if not registry:
        return {"status": "skipped", "reason": "no AI providers available"}

    # Prefer Ollama (local), then try others
    provider_order = ["ollama", "anthropic", "openai", "google"]
    available_provider = None

    for provider_name in provider_order:
        if provider_name in registry:
            provider = registry[provider_name]
            try:
                if await provider.is_available():
                    available_provider = (provider_name, provider)
                    break
            except Exception:
                continue

    if not available_provider:
        return {"status": "skipped", "reason": "no available AI providers"}

    provider_name, provider = available_provider

    # Build a fact-checking prompt
    claims_text = "\n".join([f"- {claim}" for claim in claims[:5]])
    prompt = f"""You are a fact-checking assistant. Review these claims extracted from AI-generated content and assess their credibility:

{claims_text}

Context: {context or 'No context provided'}

For each claim, provide:
1. Whether it appears plausible/verifiable
2. Any red flags or concerns
3. Overall assessment: likely accurate, questionable, or suspicious

Keep response concise."""

    try:
        # Get the first available model
        models = await provider.list_models()
        if not models:
            return {"status": "error", "reason": "no models available"}

        model = models[0]
        response = await provider.complete(prompt, model)

        # Parse response for credibility assessment
        assessment = response.content.lower()
        score_adjustment = 0

        # Simple heuristic: if response mentions "suspicious", "unlikely", "red flags", penalize
        if any(word in assessment for word in ["suspicious", "unlikely", "red flag", "questionable", "problematic"]):
            score_adjustment = -10
        # If mentions "plausible", "likely", "credible", bonus
        elif any(word in assessment for word in ["plausible", "likely accurate", "credible", "verified"]):
            score_adjustment = 5

        return {
            "status": "success",
            "provider": provider_name,
            "model": model,
            "assessment": response.content,
            "score_adjustment": score_adjustment,
            "latency_ms": response.latency_ms,
        }

    except Exception as e:
        return {"status": "error", "reason": str(e)}


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
        url_pattern = r'https?://[^\s\)"\]<>]+'
        self.urls = re.findall(url_pattern, self.content)

        citation_patterns = [
            r'\[\d+\]',
            r'\([\w\s&,]+,\s*\d{4}\)',
            r'(?:According to|Per|Via|From|Source:)\s+([^.!?]+)',
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
        patterns = [
            r'([\w\s]+)\s+(?:is|are|was|were|has|have|claimed|stated|reported|showed|found)\s+([^.!?]+)',
            r'([\d.]+)\s+(%|percent|million|billion|thousand|years?|months?)\s+([^.!?]+)',
            r'(on|in|during)\s+([^.!?]+?)\s*[,.]',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, self.content, re.IGNORECASE)
            self.claims.extend([match for match in matches if match])

    def get_claims(self) -> List[str]:
        return [' '.join(claim) if isinstance(claim, tuple) else claim for claim in self.claims[:10]]


class TrustScore:
    """Compute a trust score for AI-generated content.

    Scoring philosophy:
    - Start at 100 and deduct for problems found.
    - Well-sourced, hedged content: 85-100
    - Reasonable but unsourced claims: 60-84
    - Overconfident/unverifiable claims: 30-59
    - Obviously wrong or manipulative: 0-29
    """

    # --- word lists --------------------------------------------------------
    OVERCONFIDENT_WORDS = [
        r"\bdefinitely\b", r"\bcertainly\b", r"\babsolutely\b",
        r"\bguaranteed\b", r"\bundeniably\b", r"\bunquestionably\b",
        r"\bwithout a doubt\b", r"\bno question\b",
        r"\b100%\b", r"\bproven fact\b",
    ]
    OVERCONFIDENT_PHRASES = [
        r"\bevery expert agrees\b", r"\beveryone knows\b",
        r"\beveryone agrees\b", r"\beverybody knows\b",
        r"\bthe truth is\b", r"\bfact is\b", r"\bit is proven\b",
        r"\bscience proves\b", r"\bstudies prove\b",
        r"\bno one disagrees\b", r"\bno one denies\b",
    ]
    UNIVERSAL_QUANTIFIERS = [
        r"\ball\s+(?:people|experts|scientists|studies|evidence|problems)\b",
        r"\bevery\s+(?:person|expert|scientist|study|one)\b",
        r"\bnone\s+of\b", r"\bno one\b", r"\bnobody\b",
        r"\beveryone\s+should\b", r"\beverything\s+(?:is|will|can)\b",
    ]
    HEDGING_WORDS = [
        r"\bmay\b", r"\bmight\b", r"\bcould\b", r"\blikely\b",
        r"\bpossibly\b", r"\bprobably\b", r"\bperhaps\b",
        r"\bapproximately\b", r"\baround\b", r"\broughly\b",
        r"\bsuggests?\b", r"\bindicates?\b", r"\btends?\s+to\b",
        r"\bgenerally\b", r"\btypically\b", r"\busually\b",
        r"\boften\b", r"\bsome\b", r"\bmany\b",
        r"\bI think\b", r"\bI believe\b",
        r"\bas far as I know\b", r"\bto my knowledge\b",
    ]
    ABSOLUTE_SENTIMENT = [
        r"\bbest\b", r"\bworst\b", r"\bonly\b",
        r"\balways\b", r"\bnever\b",
    ]

    def __init__(self, content: str, context: str = None):
        self.content = content
        self.context = context
        self.issues: List[str] = []
        self.score = 100
        self.sources = SourceCitation(content)
        self.claims = ClaimExtractor(content)

    # --- helpers -----------------------------------------------------------
    def _count_matches(self, patterns: list[str]) -> int:
        return sum(
            len(re.findall(p, self.content, re.IGNORECASE))
            for p in patterns
        )

    def _penalize(self, amount: int, reason: str):
        self.score -= amount
        self.issues.append(reason)

    # --- checks ------------------------------------------------------------
    def check_overconfident_language(self):
        """Penalize overconfident words and phrases."""
        hits = self._count_matches(self.OVERCONFIDENT_WORDS)
        phrase_hits = self._count_matches(self.OVERCONFIDENT_PHRASES)
        total = hits + phrase_hits

        if total >= 3:
            self._penalize(30, f"Highly overconfident language ({total} instances)")
        elif total == 2:
            self._penalize(20, f"Overconfident language ({total} instances)")
        elif total == 1:
            self._penalize(12, "Contains overconfident language")

    def check_universal_quantifiers(self):
        """Penalize sweeping universal claims."""
        hits = self._count_matches(self.UNIVERSAL_QUANTIFIERS)
        if hits >= 3:
            self._penalize(25, f"Excessive universal claims ({hits} instances)")
        elif hits == 2:
            self._penalize(18, f"Multiple universal claims ({hits} instances)")
        elif hits == 1:
            self._penalize(10, "Contains a universal claim")

    def check_absolute_sentiment(self):
        """Penalize absolute/subjective language like 'best', 'always'."""
        hits = self._count_matches(self.ABSOLUTE_SENTIMENT)
        if hits >= 3:
            self._penalize(20, f"Multiple absolute terms ({hits} instances)")
        elif hits == 2:
            self._penalize(12, f"Absolute terms present ({hits} instances)")
        elif hits == 1:
            self._penalize(7, "Contains absolute language")

    def check_hedging_present(self):
        """Reward hedging; penalize its absence when claims are made."""
        hedge_count = self._count_matches(self.HEDGING_WORDS)
        sentences = [s.strip() for s in re.split(r'[.!?]+', self.content) if s.strip()]
        claim_sentences = len(sentences)

        if hedge_count == 0 and claim_sentences > 0:
            # No hedging at all — penalty scales with content length
            penalty = min(20, 8 + claim_sentences * 2)
            self._penalize(penalty, "No hedging or qualifying language in any claim")
        elif hedge_count > 0 and claim_sentences > 2:
            # Some hedging present — mild bonus (cap at 100 later)
            self.score = min(100, self.score + min(5, hedge_count * 2))

    def check_future_predictions(self):
        """Penalize 'will' used without hedging modals."""
        # Find "will <verb>" patterns that aren't hedged with could/might/may
        will_matches = re.findall(
            r'\b(?:will)\s+(?!not\b)(\w+)', self.content, re.IGNORECASE
        )
        hedged_future = re.findall(
            r'\b(?:might|could|may)\s+(\w+)', self.content, re.IGNORECASE
        )

        unhedged_will = len(will_matches) - len(hedged_future)
        if unhedged_will >= 3:
            self._penalize(20, f"Multiple future predictions stated as fact ({unhedged_will} unhedged)")
        elif unhedged_will == 2:
            self._penalize(12, "Future predictions stated as fact")
        elif unhedged_will == 1:
            self._penalize(7, "Contains an unhedged future prediction")

    def check_source_citations(self):
        """Penalize unsourced specific claims; reward citations."""
        source_info = self.sources.get_summary()
        has_sources = source_info["citation_count"] > 0 or source_info["url_count"] > 0

        # Count specific claims (numbers, stats, named entities)
        specific_stats = re.findall(r'\d+\.?\d*\s*%', self.content)
        specific_numbers = re.findall(r'\b\d{2,}\b', self.content)
        has_specific_claims = len(specific_stats) > 0 or len(specific_numbers) > 0

        word_count = len(self.content.split())

        if not has_sources:
            if has_specific_claims:
                self._penalize(15, "Specific numerical claims made without any source citations")
            elif word_count > 30:
                self._penalize(10, "No source citations for substantive claims")
            elif word_count > 15:
                self._penalize(5, "No sources cited")
        else:
            # Reward good sourcing
            self.score = min(100, self.score + 5)

    def check_round_suspicious_numbers(self):
        """Detect suspiciously round or exact percentages."""
        round_pcts = re.findall(
            r'\b(?:exactly\s+)?\d+0\s*%', self.content, re.IGNORECASE
        )
        exact_pcts = re.findall(
            r'\bexactly\s+\d+\.?\d*\s*%', self.content, re.IGNORECASE
        )
        pct_100 = re.findall(r'\b100\s*%\s+of\b', self.content, re.IGNORECASE)

        suspicious = len(round_pcts) + len(exact_pcts) + len(pct_100)
        if suspicious >= 2:
            self._penalize(12, "Multiple suspiciously round/exact statistics")
        elif suspicious == 1:
            self._penalize(5, "Contains a suspiciously round statistic")

    def check_specific_claims(self):
        """Flag excessive specific numbers that could be hallucinated."""
        stats = re.findall(r"\d+\.?\d*%", self.content)
        specific_years = re.findall(r"\b(19|20)\d{2}\b", self.content)

        if len(stats) > 5:
            self._penalize(10, f"Contains {len(stats)} specific statistics — verify independently")
        if len(specific_years) > 3:
            self._penalize(5, f"Contains {len(specific_years)} specific dates — double-check accuracy")

    def check_length_quality(self):
        """Very short responses to complex questions are suspicious."""
        word_count = len(self.content.split())
        if self.context and len(self.context.split()) > 20 and word_count < 10:
            self._penalize(20, "Response is unusually short for the question complexity")

    def check_repetition(self):
        """Repetitive content often indicates low-quality generation."""
        sentences = re.split(r'[.!?]+', self.content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        unique = set(s.lower() for s in sentences)
        if len(sentences) > 3 and len(unique) < len(sentences) * 0.6:
            self._penalize(15, "Content has significant repetition")

    def check_factual_consistency(self):
        """Check for contradictions within the content."""
        contradictions = [
            (r'\b(but|however|yet|although)\b.*\b(same|identical|exactly the same)\b',
             'Logical contradiction detected'),
            (r'\bwill\s+.*\b(cannot|will not)\b',
             'Future state contradiction'),
        ]
        for pattern, issue in contradictions:
            if re.search(pattern, self.content, re.IGNORECASE):
                self._penalize(8, issue)

    def check_subjective_as_objective(self):
        """Detect subjective opinions presented as objective facts."""
        # Patterns like "X is the best", "X is terrible", "everyone should"
        subjective = [
            r'\bis\s+the\s+(?:best|worst|greatest|most\s+\w+)\b',
            r'\beveryone\s+should\b',
            r'\bis\s+(?:terrible|amazing|awful|perfect|horrible)\b',
            r'\bno\s+reason\s+(?:to|for|not\s+to)\b',
            r'\bobviously\b',
            r'\bclearly\s+(?:the|superior|better|worse)\b',
        ]
        hits = self._count_matches(subjective)
        if hits >= 2:
            self._penalize(20, "Subjective opinions presented as objective facts")
        elif hits == 1:
            self._penalize(10, "Subjective claim presented as fact")

    def compute(self) -> dict:
        # Run all checks
        self.check_overconfident_language()
        self.check_universal_quantifiers()
        self.check_absolute_sentiment()
        self.check_hedging_present()
        self.check_future_predictions()
        self.check_source_citations()
        self.check_round_suspicious_numbers()
        self.check_specific_claims()
        self.check_length_quality()
        self.check_repetition()
        self.check_factual_consistency()
        self.check_subjective_as_objective()

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
        elif score >= 30:
            return "low"
        else:
            return "very_low"


@router.post("")
async def verify_content(req: VerifyRequest, db: AsyncSession = Depends(get_db)):
    """Run full verification on AI-generated content."""
    scorer = TrustScore(req.content, req.context)
    result = scorer.compute()

    # Perform AI cross-check if trust score is low
    ai_cross_check = None
    if result["score"] < 70:
        claims = result.get("claims", [])
        ai_cross_check = await perform_ai_cross_check(claims, req.context)

        # Apply score adjustment from AI assessment if successful
        if ai_cross_check.get("status") == "success":
            adjustment = ai_cross_check.get("score_adjustment", 0)
            result["score"] = max(0, min(100, result["score"] + adjustment))

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
        "hallucination_score": 100 - result["score"],
        "ai_cross_check": ai_cross_check,
    }


@router.post("/batch")
async def verify_batch(items: list[VerifyRequest], db: AsyncSession = Depends(get_db)):
    """Verify multiple responses (for model comparison)."""
    results = []
    for item in items:
        scorer = TrustScore(item.content, item.context)
        result = scorer.compute()

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
