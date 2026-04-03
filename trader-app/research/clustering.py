"""Narrative clustering — group related items into market narratives."""
from __future__ import annotations

import re
from collections import defaultdict
from difflib import SequenceMatcher
from datetime import datetime

from research.models import (
    InfluenceType,
    NarrativeCluster,
    NormalizedItem,
    SentimentDirection,
)


# ── Keyword-based theme detection ──────────────────────────

NARRATIVE_KEYWORDS: dict[str, dict] = {
    "fed_rates": {
        "keywords": ["fed", "fomc", "rate", "interest rate", "powell", "hawkish", "dovish",
                      "tightening", "easing", "monetary policy", "fed funds"],
        "influence_type": InfluenceType.POLICY,
        "label_template": "Fed rate expectations / monetary policy",
    },
    "inflation": {
        "keywords": ["inflation", "cpi", "ppi", "consumer price", "deflation",
                      "inflationary", "price pressure"],
        "influence_type": InfluenceType.MACRO,
        "label_template": "Inflation data and expectations",
    },
    "labor_market": {
        "keywords": ["jobs", "employment", "unemployment", "nonfarm", "payroll",
                      "jobless claims", "labor market", "hiring"],
        "influence_type": InfluenceType.MACRO,
        "label_template": "Labor market conditions",
    },
    "oil_energy": {
        "keywords": ["oil", "crude", "opec", "energy", "natural gas", "petroleum",
                      "brent", "wti"],
        "influence_type": InfluenceType.GEOPOLITICAL,
        "label_template": "Oil / energy market dynamics",
    },
    "tech_sector": {
        "keywords": ["tech", "semiconductor", "chip", "ai ", "artificial intelligence",
                      "nvidia", "apple", "microsoft", "google", "meta", "amazon",
                      "nasdaq", "qqq", "magnificent"],
        "influence_type": InfluenceType.SECTOR,
        "label_template": "Technology sector dynamics",
    },
    "china": {
        "keywords": ["china", "beijing", "chinese", "yuan", "renminbi", "pboc",
                      "stimulus", "trade war", "tariff"],
        "influence_type": InfluenceType.GEOPOLITICAL,
        "label_template": "China / trade policy developments",
    },
    "europe": {
        "keywords": ["ecb", "eurozone", "europe", "euro ", "lagarde", "eu ",
                      "germany", "dax", "ftse"],
        "influence_type": InfluenceType.GEOPOLITICAL,
        "label_template": "European economic developments",
    },
    "japan": {
        "keywords": ["japan", "boj", "yen", "nikkei", "ueda", "kuroda"],
        "influence_type": InfluenceType.GEOPOLITICAL,
        "label_template": "Japan / BOJ policy",
    },
    "geopolitical_risk": {
        "keywords": ["war", "conflict", "tension", "sanction", "military",
                      "missile", "nuclear", "middle east", "ukraine", "russia"],
        "influence_type": InfluenceType.GEOPOLITICAL,
        "label_template": "Geopolitical risk / conflict",
    },
    "earnings": {
        "keywords": ["earnings", "revenue", "guidance", "beat", "miss",
                      "quarterly results", "profit", "eps"],
        "influence_type": InfluenceType.EARNINGS,
        "label_template": "Earnings season / corporate results",
    },
    "bonds_treasuries": {
        "keywords": ["treasury", "bond", "yield", "10-year", "2-year",
                      "yield curve", "tlt", "fixed income"],
        "influence_type": InfluenceType.MACRO,
        "label_template": "Bond market / Treasury yields",
    },
    "crypto": {
        "keywords": ["bitcoin", "crypto", "ethereum", "btc", "digital asset"],
        "influence_type": InfluenceType.SECTOR,
        "label_template": "Cryptocurrency market",
    },
    "commodities": {
        "keywords": ["gold", "silver", "copper", "commodity", "commodities",
                      "metals", "wheat", "agriculture"],
        "influence_type": InfluenceType.MACRO,
        "label_template": "Commodities market",
    },
}


def _match_narrative(text: str) -> list[str]:
    """Return narrative keys that match the text."""
    text_lower = text.lower()
    matches = []
    for key, cfg in NARRATIVE_KEYWORDS.items():
        if any(kw in text_lower for kw in cfg["keywords"]):
            matches.append(key)
    return matches


def _aggregate_sentiment(items: list[NormalizedItem]) -> SentimentDirection:
    """Determine aggregate sentiment from a list of items."""
    counts = defaultdict(int)
    for item in items:
        counts[item.sentiment] += 1
    if not counts:
        return SentimentDirection.NEUTRAL
    # Weighted: bullish/bearish count, with neutral as tiebreaker
    bull = counts.get(SentimentDirection.BULLISH, 0)
    bear = counts.get(SentimentDirection.BEARISH, 0)
    if bull > bear:
        return SentimentDirection.BULLISH
    elif bear > bull:
        return SentimentDirection.BEARISH
    elif bull == bear and bull > 0:
        return SentimentDirection.MIXED
    return SentimentDirection.NEUTRAL


def cluster_items(items: list[NormalizedItem]) -> list[NarrativeCluster]:
    """Cluster items into narrative groups based on keyword matching."""
    buckets: dict[str, list[NormalizedItem]] = defaultdict(list)
    unclustered: list[NormalizedItem] = []

    for item in items:
        text = f"{item.title} {item.summary}"
        matches = _match_narrative(text)
        if matches:
            for key in matches:
                buckets[key].append(item)
        else:
            unclustered.append(item)

    clusters: list[NarrativeCluster] = []

    for key, bucket_items in buckets.items():
        if not bucket_items:
            continue
        cfg = NARRATIVE_KEYWORDS[key]

        # Collect all affected assets and regions
        all_symbols: set[str] = set()
        all_regions: set[str] = set()
        for item in bucket_items:
            all_symbols.update(item.symbols)
            all_regions.update(item.regions)

        # Timestamp range
        timestamps = [i.published_at for i in bucket_items if i.published_at]
        ts_start = min(timestamps) if timestamps else None
        ts_end = max(timestamps) if timestamps else None

        # Influence score: average trust * cross-source confirmation bonus
        avg_trust = sum(i.trust_score for i in bucket_items) / len(bucket_items)
        unique_sources = len({i.source for i in bucket_items})
        cross_source_bonus = min(0.3, unique_sources * 0.1)
        influence = min(1.0, avg_trust + cross_source_bonus)

        cluster = NarrativeCluster(
            label=cfg["label_template"],
            items=bucket_items,
            aggregate_sentiment=_aggregate_sentiment(bucket_items),
            affected_assets=sorted(all_symbols),
            regions=sorted(all_regions),
            macro_tags=[key],
            influence_type=cfg["influence_type"],
            influence_score=round(influence, 3),
            confidence=round(min(1.0, len(bucket_items) / 5), 2),  # more items = more confident
            timestamp_start=ts_start,
            timestamp_end=ts_end,
        )
        clusters.append(cluster)

    # Sort by influence score descending
    clusters.sort(key=lambda c: c.influence_score, reverse=True)

    # Add unclustered items as individual "misc" cluster if any
    if unclustered:
        clusters.append(NarrativeCluster(
            label="Other market developments",
            items=unclustered,
            aggregate_sentiment=_aggregate_sentiment(unclustered),
            influence_score=0.1,
            confidence=0.2,
        ))

    return clusters
