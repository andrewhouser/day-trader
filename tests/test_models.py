"""Tests for research domain models."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime
from research.models import (
    NormalizedItem,
    NarrativeCluster,
    MarketReport,
    SourceCategory,
    SourceType,
    SentimentDirection,
    InfluenceType,
)


def test_normalized_item_defaults():
    item = NormalizedItem(title="Test", summary="Summary")
    assert item.title == "Test"
    assert item.category == SourceCategory.NEWS
    assert item.source_type == SourceType.SECONDARY
    assert item.sentiment == SentimentDirection.NEUTRAL
    assert item.trust_score == 0.5
    assert isinstance(item.id, str)
    assert len(item.id) == 12


def test_normalized_item_to_dict():
    item = NormalizedItem(
        title="Fed raises rates",
        summary="The Federal Reserve raised rates by 25bps",
        source="fred",
        category=SourceCategory.MACRO,
        source_type=SourceType.PRIMARY,
        published_at=datetime(2026, 4, 3, 12, 0),
        url="https://fred.stlouisfed.org/series/FEDFUNDS",
        symbols=["SPY", "TLT"],
        regions=["US"],
        themes=["rates", "macro"],
        sentiment=SentimentDirection.BEARISH,
        trust_score=0.95,
        influence_score=0.8,
    )
    d = item.to_dict()
    assert d["title"] == "Fed raises rates"
    assert d["category"] == "macro"
    assert d["source_type"] == "primary"
    assert d["sentiment"] == "bearish"
    assert d["trust_score"] == 0.95
    assert d["symbols"] == ["SPY", "TLT"]
    assert d["published_at"] == "2026-04-03T12:00:00"


def test_narrative_cluster_to_dict():
    items = [
        NormalizedItem(title="A", source="reuters"),
        NormalizedItem(title="B", source="finnhub"),
    ]
    cluster = NarrativeCluster(
        label="Fed rate expectations",
        items=items,
        aggregate_sentiment=SentimentDirection.BEARISH,
        affected_assets=["SPY", "TLT"],
        regions=["US"],
        influence_type=InfluenceType.POLICY,
        influence_score=0.85,
        confidence=0.7,
    )
    d = cluster.to_dict()
    assert d["label"] == "Fed rate expectations"
    assert d["item_count"] == 2
    assert set(d["sources"]) == {"reuters", "finnhub"}
    assert d["aggregate_sentiment"] == "bearish"
    assert d["influence_score"] == 0.85
