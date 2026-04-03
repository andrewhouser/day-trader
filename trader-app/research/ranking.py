"""Ranking heuristics — score and rank items and clusters."""
from __future__ import annotations

from datetime import datetime

from research.models import NarrativeCluster, NormalizedItem, SourceType


def rank_items(items: list[NormalizedItem]) -> list[NormalizedItem]:
    """Rank items by a composite score combining freshness, trust,
    cross-source confirmation, and category weight."""
    now = datetime.utcnow()

    for item in items:
        score = 0.0

        # 1. Trust score (0–1) — weighted 40%
        score += item.trust_score * 0.4

        # 2. Freshness (0–1) — weighted 30%
        if item.published_at:
            age_hours = max(0, (now - item.published_at).total_seconds() / 3600)
            freshness = max(0, 1.0 - (age_hours / 48))  # decays over 48h
        else:
            freshness = 0.3  # unknown age gets moderate score
        score += freshness * 0.3

        # 3. Source type bonus — weighted 15%
        type_bonus = {
            SourceType.PRIMARY: 1.0,
            SourceType.SECONDARY: 0.5,
            SourceType.OPINION: 0.2,
        }
        score += type_bonus.get(item.source_type, 0.3) * 0.15

        # 4. Symbol/region breadth — weighted 15%
        breadth = min(1.0, (len(item.symbols) + len(item.regions)) / 6)
        score += breadth * 0.15

        item.influence_score = round(score, 4)

    items.sort(key=lambda x: x.influence_score, reverse=True)
    return items


def rank_clusters(clusters: list[NarrativeCluster]) -> list[NarrativeCluster]:
    """Rank narrative clusters by composite influence."""
    for cluster in clusters:
        base = cluster.influence_score

        # Boost for cross-source confirmation
        unique_sources = len({i.source for i in cluster.items})
        confirmation_bonus = min(0.2, unique_sources * 0.05)

        # Boost for breadth of affected assets
        asset_bonus = min(0.15, len(cluster.affected_assets) * 0.03)

        # Boost for regional breadth
        region_bonus = min(0.1, len(cluster.regions) * 0.025)

        cluster.influence_score = round(
            min(1.0, base + confirmation_bonus + asset_bonus + region_bonus), 3
        )

    clusters.sort(key=lambda c: c.influence_score, reverse=True)
    return clusters
