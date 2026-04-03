"""Tests for narrative clustering logic."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime
from research.models import NormalizedItem, SentimentDirection, InfluenceType
from research.clustering import cluster_items, _match_narrative, _aggregate_sentiment


def test_match_narrative_fed():
    matches = _match_narrative("Fed raises interest rate by 25bps, Powell signals more hikes")
    assert "fed_rates" in matches


def test_match_narrative_oil():
    matches = _match_narrative("Oil prices surge as OPEC cuts production")
    assert "oil_energy" in matches


def test_match_narrative_tech():
    matches = _match_narrative("NVIDIA reports record AI chip revenue, Nasdaq rallies")
    assert "tech_sector" in matches


def test_match_narrative_multiple():
    matches = _match_narrative("Fed rate decision impacts tech stocks and bond yields")
    assert "fed_rates" in matches
    assert "tech_sector" in matches


def test_match_narrative_no_match():
    matches = _match_narrative("Local weather forecast for tomorrow")
    assert len(matches) == 0


def test_cluster_items_groups_by_narrative():
    items = [
        NormalizedItem(title="Fed raises rates", summary="FOMC decision", source="reuters"),
        NormalizedItem(title="Powell signals hawkish stance", summary="Fed chair comments", source="finnhub"),
        NormalizedItem(title="Oil surges on OPEC cuts", summary="Crude prices up", source="reuters"),
    ]
    clusters = cluster_items(items)
    labels = [c.label for c in clusters]
    assert any("Fed" in l or "monetary" in l for l in labels)
    assert any("Oil" in l or "energy" in l for l in labels)


def test_cluster_items_unclustered():
    items = [
        NormalizedItem(title="Random unrelated headline about sports"),
    ]
    clusters = cluster_items(items)
    assert len(clusters) == 1
    assert clusters[0].label == "Other market developments"


def test_aggregate_sentiment_bullish():
    items = [
        NormalizedItem(sentiment=SentimentDirection.BULLISH),
        NormalizedItem(sentiment=SentimentDirection.BULLISH),
        NormalizedItem(sentiment=SentimentDirection.NEUTRAL),
    ]
    assert _aggregate_sentiment(items) == SentimentDirection.BULLISH


def test_aggregate_sentiment_mixed():
    items = [
        NormalizedItem(sentiment=SentimentDirection.BULLISH),
        NormalizedItem(sentiment=SentimentDirection.BEARISH),
    ]
    assert _aggregate_sentiment(items) == SentimentDirection.MIXED


def test_cluster_influence_score():
    items = [
        NormalizedItem(title="Fed raises rates", source="reuters", trust_score=0.9),
        NormalizedItem(title="FOMC hawkish", source="fred", trust_score=0.98),
    ]
    clusters = cluster_items(items)
    fed_cluster = [c for c in clusters if "Fed" in c.label or "monetary" in c.label]
    assert len(fed_cluster) == 1
    # Cross-source bonus should boost influence
    assert fed_cluster[0].influence_score > 0.8
