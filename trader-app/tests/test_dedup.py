"""Tests for deduplication logic."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from research.models import NormalizedItem, SourceType
from research.dedup import deduplicate


def test_exact_duplicates_removed():
    items = [
        NormalizedItem(title="Fed raises rates by 25bps", source="reuters", trust_score=0.9),
        NormalizedItem(title="Fed raises rates by 25bps", source="finnhub", trust_score=0.7),
    ]
    result = deduplicate(items)
    assert len(result) == 1
    # Should keep the higher-trust one
    assert result[0].source == "reuters"


def test_near_duplicates_removed():
    items = [
        NormalizedItem(title="Federal Reserve raises interest rates by 25 basis points", trust_score=0.9),
        NormalizedItem(title="Federal Reserve raises interest rates by 25 basis points today", trust_score=0.7),
    ]
    result = deduplicate(items)
    assert len(result) == 1


def test_different_items_kept():
    items = [
        NormalizedItem(title="Fed raises rates by 25bps"),
        NormalizedItem(title="Oil prices surge on Middle East tensions"),
        NormalizedItem(title="Tech stocks rally on strong earnings"),
    ]
    result = deduplicate(items)
    assert len(result) == 3


def test_empty_input():
    assert deduplicate([]) == []


def test_primary_source_preferred():
    items = [
        NormalizedItem(
            title="Unemployment rate falls to 3.5%",
            source="blog",
            source_type=SourceType.OPINION,
            trust_score=0.3,
        ),
        NormalizedItem(
            title="Unemployment rate falls to 3.5%",
            source="bls",
            source_type=SourceType.PRIMARY,
            trust_score=0.98,
        ),
    ]
    result = deduplicate(items)
    assert len(result) == 1
    assert result[0].source == "bls"
