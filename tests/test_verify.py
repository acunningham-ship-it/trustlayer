"""Tests for the Verification Engine."""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.routers.verify import TrustScore


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
