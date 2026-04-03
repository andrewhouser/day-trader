"""Tests for ranking heuristics."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta
from research.models import NormalizedItem, NarrativeCluster, SourceType
from research.ranking import rank_items, rank_clusters


def test_rank_items_freshness():
    now = datetime.utcnow()
    fresh = NormalizedItem(
        title="Fresh news", published_at=now - timedelta(minutes=30), trust_score=0.7
    )
    stale = NormalizedItem(
        title="Old news", published_at=now - timedelta(hours=40), trust_score=0.7
    )
    ranked = rank_items([stale, fresh])
    assert ranked[0].title == "Fresh news"


def test_rank_items_trust():
    now = datetime.utcnow()
    high_trust = NormalizedItem(
        title="Primary source", trust_score=0.95,
        source_type=SourceType.PRIMARY, published_at=now
    )
    low_trust = NormalizedItem(
        title="Opinion piece", trust_score=0.3,
        source_type=SourceType.OPINION, published_at=now
    )
    ranked = rank_items([low_trust, high_trust])
    assert ranked[0].title == "Primary source"
    assert ranked[0].influence_score > ranked[1].influence_score


def test_rank_clusters_cross_source_bonus():
    c1 = NarrativeCluster(
        label="Single source",
        items=[NormalizedItem(source="reuters")],
        influence_score=0.5,
    )
    c2 = NarrativeCluster(
        label="Multi source",
        items=[
            NormalizedItem(source="reuters"),
            NormalizedItem(source="finnhub"),
            NormalizedItem(source="fred"),
        ],
        influence_score=0.5,
        affected_assets=["SPY", "QQQ"],
        regions=["US", "EU"],
    )
    ranked = rank_clusters([c1, c2])
    assert ranked[0].label == "Multi source"
    assert ranked[0].influence_score > ranked[1].influence_score
