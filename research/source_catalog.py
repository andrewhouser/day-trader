"""Source catalog — trust metadata for every data source."""
from __future__ import annotations

from typing import Optional

from .models import SourceCategory, SourceMeta, SourceType

# ── Source trust registry ──────────────────────────────────
# reliability: 0.0–1.0 (higher = more trusted)
# Sources are grouped by category per the spec.

SOURCE_CATALOG: dict[str, SourceMeta] = {
    # ── A. Financial news ──────────────────────────────────
    "reuters": SourceMeta(
        name="Reuters",
        category=SourceCategory.NEWS,
        source_type=SourceType.SECONDARY,
        reliability=0.90,
        coverage_regions=["US", "EU", "ASIA", "GLOBAL"],
    ),
    "marketwatch": SourceMeta(
        name="MarketWatch",
        category=SourceCategory.NEWS,
        source_type=SourceType.SECONDARY,
        reliability=0.75,
        coverage_regions=["US"],
    ),
    "investing_com": SourceMeta(
        name="Investing.com",
        category=SourceCategory.NEWS,
        source_type=SourceType.SECONDARY,
        reliability=0.70,
        coverage_regions=["US", "EU", "ASIA", "GLOBAL"],
    ),
    "seeking_alpha": SourceMeta(
        name="Seeking Alpha",
        category=SourceCategory.NEWS,
        source_type=SourceType.OPINION,
        reliability=0.55,
        opinion_heavy=True,
        coverage_regions=["US"],
    ),
    # ── B. Macro / economic data ───────────────────────────
    "fred": SourceMeta(
        name="FRED (Federal Reserve Economic Data)",
        category=SourceCategory.MACRO,
        source_type=SourceType.PRIMARY,
        reliability=0.98,
        coverage_regions=["US"],
    ),
    "bls": SourceMeta(
        name="Bureau of Labor Statistics",
        category=SourceCategory.MACRO,
        source_type=SourceType.PRIMARY,
        reliability=0.98,
        coverage_regions=["US"],
    ),
    "trading_economics": SourceMeta(
        name="Trading Economics",
        category=SourceCategory.MACRO,
        source_type=SourceType.SECONDARY,
        reliability=0.80,
        coverage_regions=["US", "EU", "ASIA", "GLOBAL"],
    ),
    "world_bank": SourceMeta(
        name="World Bank",
        category=SourceCategory.MACRO,
        source_type=SourceType.PRIMARY,
        reliability=0.95,
        coverage_regions=["GLOBAL"],
    ),
    # ── C. Market data / quantitative ──────────────────────
    "alpha_vantage": SourceMeta(
        name="Alpha Vantage",
        category=SourceCategory.MARKET_DATA,
        source_type=SourceType.PRIMARY,
        reliability=0.85,
        coverage_regions=["US", "GLOBAL"],
    ),
    "finnhub": SourceMeta(
        name="Finnhub",
        category=SourceCategory.MARKET_DATA,
        source_type=SourceType.PRIMARY,
        reliability=0.85,
        coverage_regions=["US", "EU", "GLOBAL"],
    ),
    "yfinance": SourceMeta(
        name="Yahoo Finance (yfinance)",
        category=SourceCategory.MARKET_DATA,
        source_type=SourceType.SECONDARY,
        reliability=0.70,
        coverage_regions=["US", "EU", "ASIA", "GLOBAL"],
    ),
    # ── D. Sentiment / market psychology ───────────────────
    "finviz": SourceMeta(
        name="Finviz",
        category=SourceCategory.SENTIMENT,
        source_type=SourceType.SECONDARY,
        reliability=0.65,
        coverage_regions=["US"],
    ),
    "reddit": SourceMeta(
        name="Reddit (investing communities)",
        category=SourceCategory.SENTIMENT,
        source_type=SourceType.OPINION,
        reliability=0.35,
        opinion_heavy=True,
        coverage_regions=["US"],
    ),
    # ── E. Primary-source filings ──────────────────────────
    "sec_edgar": SourceMeta(
        name="SEC EDGAR",
        category=SourceCategory.FILINGS,
        source_type=SourceType.PRIMARY,
        reliability=0.99,
        coverage_regions=["US"],
    ),
    # ── F. Geopolitical / policy ───────────────────────────
    "imf": SourceMeta(
        name="International Monetary Fund",
        category=SourceCategory.GEOPOLITICAL,
        source_type=SourceType.PRIMARY,
        reliability=0.95,
        coverage_regions=["GLOBAL"],
    ),
    "fed": SourceMeta(
        name="Federal Reserve",
        category=SourceCategory.GEOPOLITICAL,
        source_type=SourceType.PRIMARY,
        reliability=0.99,
        coverage_regions=["US"],
    ),
    "ecb": SourceMeta(
        name="European Central Bank",
        category=SourceCategory.GEOPOLITICAL,
        source_type=SourceType.PRIMARY,
        reliability=0.97,
        coverage_regions=["EU"],
    ),
    "boj": SourceMeta(
        name="Bank of Japan",
        category=SourceCategory.GEOPOLITICAL,
        source_type=SourceType.PRIMARY,
        reliability=0.97,
        coverage_regions=["ASIA"],
    ),
    "boe": SourceMeta(
        name="Bank of England",
        category=SourceCategory.GEOPOLITICAL,
        source_type=SourceType.PRIMARY,
        reliability=0.97,
        coverage_regions=["UK"],
    ),
}


def get_source_meta(source_key: str) -> "Optional[SourceMeta]":
    return SOURCE_CATALOG.get(source_key)


def get_enabled_sources(category: "Optional[SourceCategory]" = None) -> dict[str, SourceMeta]:
    return {
        k: v for k, v in SOURCE_CATALOG.items()
        if v.enabled and (category is None or v.category == category)
    }
