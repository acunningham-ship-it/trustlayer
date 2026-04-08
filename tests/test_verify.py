"""Tests for the Verification Engine."""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.routers.verify import TrustScore, SourceCitation, ClaimExtractor


def test_high_trust_simple_factual():
    ts = TrustScore("The sky appears blue due to Rayleigh scattering of sunlight.")
    result = ts.compute()
    assert result["score"] >= 75
    assert result["label"] in ("high", "medium")


def test_low_trust_overconfident():
    ts = TrustScore(
        "The stock market will definitely always go up. This is guaranteed. "
        "100% certain this will happen. Never any exceptions. Always profitable."
    )
    result = ts.compute()
    assert result["score"] <= 85
    assert len(result["issues"]) > 0


def test_repetition_detected():
    ts = TrustScore(
        "AI is amazing. AI is incredible. AI is amazing. AI is fantastic. "
        "AI is amazing. AI is incredible."
    )
    result = ts.compute()
    # Should flag repetition
    repetition_issues = [i for i in result["issues"] if "repetition" in i.lower()]
    assert len(repetition_issues) > 0


def test_many_stats_flagged():
    ts = TrustScore(
        "Studies show 43% of people use AI daily. 67% of companies rely on ML. "
        "82% of developers use AI tools. 91% improvement in productivity. "
        "57% reduction in errors. 34% cost savings."
    )
    result = ts.compute()
    stat_issues = [i for i in result["issues"] if "statistic" in i.lower()]
    assert len(stat_issues) > 0


def test_word_count_in_result():
    text = "Hello world this is a test"
    ts = TrustScore(text)
    result = ts.compute()
    assert result["word_count"] == 6


def test_score_bounds():
    ts = TrustScore("x")
    result = ts.compute()
    assert 0 <= result["score"] <= 100


def test_content_hash_stable():
    text = "Some AI output"
    ts1 = TrustScore(text)
    ts2 = TrustScore(text)
    assert ts1.compute()["content_hash"] == ts2.compute()["content_hash"]


def test_label_mapping():
    # High score -> high label
    ts = TrustScore("Simple factual statement.")
    result = ts.compute()
    if result["score"] >= 85:
        assert result["label"] == "high"
    elif result["score"] >= 60:
        assert result["label"] == "medium"
    else:
        assert result["label"] == "low"


def test_source_citation_extraction():
    """Test extraction of source citations and URLs."""
    content = (
        "As reported by Smith et al. (2020), the rate is 45%. "
        "See https://example.com for details. [1] Citation here."
    )
    citation = SourceCitation(content)
    summary = citation.get_summary()
    assert summary["url_count"] >= 1
    assert "https://example.com" in summary["urls"]
    assert summary["citation_count"] >= 1


def test_claim_extraction():
    """Test extraction of key claims."""
    content = (
        "The economy grew 3.2% in Q1. On January 15, the market rose significantly. "
        "Companies reported 45% higher earnings."
    )
    extractor = ClaimExtractor(content)
    claims = extractor.get_claims()
    assert len(claims) > 0
    # At least one claim should contain quantitative data
    claim_str = ' '.join(str(c) for c in claims)
    assert any(num in claim_str for num in ['3.2', '45'])


def test_factual_consistency_check():
    """Test detection of contradictions."""
    content = "This is true but it is also false. However, it must be exactly the same."
    ts = TrustScore(content)
    result = ts.compute()
    # Should detect contradiction
    contradiction_issues = [i for i in result["issues"] if "contradiction" in i.lower()]
    assert len(contradiction_issues) > 0
    assert result["score"] < 100


def test_source_citation_scoring():
    """Test that proper citations improve score."""
    content_no_source = "AI is the future. It will revolutionize everything."
    content_with_source = (
        "As reported by Smith et al. (2022) at https://example.com, "
        "AI is advancing rapidly. [1] It will transform industries."
    )

    ts_no = TrustScore(content_no_source)
    result_no = ts_no.compute()

    ts_with = TrustScore(content_with_source)
    result_with = ts_with.compute()

    # Content with sources should score better
    assert result_with["score"] >= result_no["score"]


def test_hallucinated_entities():
    """Test detection of suspicious entity patterns."""
    content = (
        "According to Dr. John Smith of ACME 123, there is XYZ 456 in Pleasantshire. "
        "The findings were published in RESEARCH 789 journal."
    )
    ts = TrustScore(content)
    result = ts.compute()
    entity_issues = [i for i in result["issues"] if "fabricated" in i.lower()]
    assert len(entity_issues) > 0


def test_verify_result_has_new_fields():
    """Test that verification result includes new fields."""
    ts = TrustScore("Check this content https://example.com for details.")
    result = ts.compute()
    assert "claims" in result
    assert "sources" in result
    assert isinstance(result["claims"], list)
    assert "urls" in result["sources"]
    assert "citation_count" in result["sources"]
