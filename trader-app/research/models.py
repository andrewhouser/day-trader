"""Domain models for the market research engine."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class SourceCategory(str, Enum):
    NEWS = "news"
    MACRO = "macro"
    MARKET_DATA = "market_data"
    SENTIMENT = "sentiment"
    FILINGS = "filings"
    GEOPOLITICAL = "geopolitical"


class SourceType(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    OPINION = "opinion"


class SentimentDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    MIXED = "mixed"
    NEUTRAL = "neutral"


class InfluenceType(str, Enum):
    MACRO = "macro"
    GEOPOLITICAL = "geopolitical"
    EARNINGS = "earnings"
    POLICY = "policy"
    SECTOR = "sector"
    IDIOSYNCRATIC = "idiosyncratic"


@dataclass
class SourceMeta:
    """Metadata describing a data source's trustworthiness and characteristics."""
    name: str
    category: SourceCategory
    source_type: SourceType
    reliability: float  # 0.0–1.0
    opinion_heavy: bool = False
    latency_seconds: int = 0  # typical freshness lag
    coverage_regions: list[str] = field(default_factory=lambda: ["US"])
    enabled: bool = True


@dataclass
class NormalizedItem:
    """A single piece of market-relevant information from any source."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    summary: str = ""
    source: str = ""
    category: SourceCategory = SourceCategory.NEWS
    source_type: SourceType = SourceType.SECONDARY
    published_at: Optional[datetime] = None
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    url: str = ""
    symbols: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)
    sentiment: SentimentDirection = SentimentDirection.NEUTRAL
    trust_score: float = 0.5
    influence_score: float = 0.0
    raw_payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "source": self.source,
            "category": self.category.value,
            "source_type": self.source_type.value,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "fetched_at": self.fetched_at.isoformat(),
            "url": self.url,
            "symbols": self.symbols,
            "regions": self.regions,
            "themes": self.themes,
            "sentiment": self.sentiment.value,
            "trust_score": self.trust_score,
            "influence_score": self.influence_score,
        }


@dataclass
class NarrativeCluster:
    """A group of related items describing a single market narrative."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    label: str = ""
    items: list[NormalizedItem] = field(default_factory=list)
    aggregate_sentiment: SentimentDirection = SentimentDirection.NEUTRAL
    affected_assets: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    macro_tags: list[str] = field(default_factory=list)
    influence_type: InfluenceType = InfluenceType.MACRO
    influence_score: float = 0.0
    confidence: float = 0.0
    timestamp_start: Optional[datetime] = None
    timestamp_end: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "item_count": len(self.items),
            "sources": list({i.source for i in self.items}),
            "aggregate_sentiment": self.aggregate_sentiment.value,
            "affected_assets": self.affected_assets,
            "regions": self.regions,
            "macro_tags": self.macro_tags,
            "influence_type": self.influence_type.value,
            "influence_score": self.influence_score,
            "confidence": self.confidence,
            "timestamp_start": self.timestamp_start.isoformat() if self.timestamp_start else None,
            "timestamp_end": self.timestamp_end.isoformat() if self.timestamp_end else None,
            "citations": [{"source": i.source, "title": i.title, "url": i.url} for i in self.items],
        }


@dataclass
class MarketReport:
    """Final synthesized market report."""
    generated_at: datetime = field(default_factory=datetime.utcnow)
    market_scope: str = "global"
    top_narratives: list[NarrativeCluster] = field(default_factory=list)
    top_macro_releases: list[NormalizedItem] = field(default_factory=list)
    top_company_catalysts: list[NormalizedItem] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    bullish_factors: list[str] = field(default_factory=list)
    bearish_factors: list[str] = field(default_factory=list)
    all_items: list[NormalizedItem] = field(default_factory=list)
    human_summary: str = ""

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at.isoformat(),
            "market_scope": self.market_scope,
            "top_narratives": [n.to_dict() for n in self.top_narratives],
            "top_macro_releases": [i.to_dict() for i in self.top_macro_releases],
            "top_company_catalysts": [i.to_dict() for i in self.top_company_catalysts],
            "risk_factors": self.risk_factors,
            "bullish_factors": self.bullish_factors,
            "bearish_factors": self.bearish_factors,
            "total_items": len(self.all_items),
            "human_summary": self.human_summary,
        }
