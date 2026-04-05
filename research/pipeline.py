"""Research pipeline — orchestrates fetch → parse → normalize → dedup → cluster → rank → report."""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from research.adapters.base import AdapterResult, SourceAdapter
from research.adapters.fred_adapter import FredAdapter
from research.adapters.finnhub_adapter import FinnhubNewsAdapter
from research.adapters.sec_edgar_adapter import SecEdgarAdapter
from research.adapters.alpha_vantage_adapter import AlphaVantageNewsAdapter
from research.adapters.finviz_adapter import FinvizAdapter
from research.adapters.reuters_adapter import ReutersAdapter
from research.adapters.investing_com_adapter import InvestingComAdapter
from research.cache import CACHE_TTLS, research_cache
from research.clustering import cluster_items
from research.dedup import deduplicate
from research.models import (
    MarketReport,
    NarrativeCluster,
    NormalizedItem,
    SourceCategory,
)
from research.ranking import rank_clusters, rank_items

logger = logging.getLogger(__name__)


def _get_default_adapters() -> list[SourceAdapter]:
    """Return the MVP set of adapters."""
    return [
        FredAdapter(),
        FinnhubNewsAdapter(),
        SecEdgarAdapter(),
        AlphaVantageNewsAdapter(),
        FinvizAdapter(),
        ReutersAdapter(),
        InvestingComAdapter(),
    ]


def fetch_all(
    adapters: list[SourceAdapter] | None = None,
    max_workers: int = 5,
) -> tuple[list[NormalizedItem], list[dict]]:
    """Run all adapters concurrently. Returns (items, diagnostics)."""
    adapters = adapters or _get_default_adapters()
    all_items: list[NormalizedItem] = []
    diagnostics: list[dict] = []

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(adapter.run): adapter for adapter in adapters}
        for future in as_completed(futures):
            adapter = futures[future]
            try:
                result: AdapterResult = future.result(timeout=60)
                all_items.extend(result.items)
                diagnostics.append(result.to_dict())
            except Exception as e:
                logger.error(f"Adapter {adapter.source_key} failed: {e}")
                diagnostics.append({
                    "source": adapter.source_key,
                    "items_count": 0,
                    "fetch_success": False,
                    "error": str(e),
                })

    logger.info(f"Fetched {len(all_items)} total items from {len(adapters)} adapters")
    return all_items, diagnostics


def run_pipeline(
    adapters: list[SourceAdapter] | None = None,
    scope: str = "global",
    use_cache: bool = True,
) -> MarketReport:
    """Execute the full research pipeline and produce a MarketReport.

    Stages: fetch → dedup → rank items → cluster → rank clusters → build report.
    """
    cache_key = f"market_report:{scope}"
    if use_cache:
        cached = research_cache.get(cache_key)
        if cached:
            logger.info("Returning cached market report")
            return cached

    t0 = time.time()

    # 1. Fetch from all sources
    raw_items, diagnostics = fetch_all(adapters)

    # 2. Deduplicate
    deduped = deduplicate(raw_items)
    dup_count = len(raw_items) - len(deduped)
    logger.info(f"Deduplication removed {dup_count} items ({len(deduped)} remaining)")

    # 3. Rank individual items
    ranked_items = rank_items(deduped)

    # 4. Cluster into narratives
    clusters = cluster_items(ranked_items)

    # 5. Rank clusters
    ranked_clusters = rank_clusters(clusters)

    # 6. Build report
    report = _build_report(ranked_items, ranked_clusters, scope, diagnostics)

    elapsed = time.time() - t0
    logger.info(f"Pipeline completed in {elapsed:.1f}s — "
                f"{len(ranked_items)} items, {len(ranked_clusters)} clusters")

    if use_cache:
        research_cache.set(cache_key, report, CACHE_TTLS["market_report"])

    return report


def _build_report(
    items: list[NormalizedItem],
    clusters: list[NarrativeCluster],
    scope: str,
    diagnostics: list[dict],
) -> MarketReport:
    """Assemble the final MarketReport from ranked items and clusters."""
    # Separate macro releases and company catalysts
    macro_items = [i for i in items if i.category in (SourceCategory.MACRO, SourceCategory.GEOPOLITICAL)]
    company_items = [i for i in items if i.category == SourceCategory.FILINGS]

    # Extract risk/bullish/bearish factors from top clusters
    risk_factors = []
    bullish_factors = []
    bearish_factors = []

    for cluster in clusters[:10]:
        label = cluster.label
        sentiment = cluster.aggregate_sentiment.value
        score = cluster.influence_score

        if sentiment == "bearish":
            bearish_factors.append(f"{label} (influence: {score})")
            risk_factors.append(label)
        elif sentiment == "bullish":
            bullish_factors.append(f"{label} (influence: {score})")
        elif sentiment == "mixed":
            risk_factors.append(f"{label} — mixed signals (influence: {score})")

    return MarketReport(
        market_scope=scope,
        top_narratives=clusters[:10],
        top_macro_releases=macro_items[:10],
        top_company_catalysts=company_items[:10],
        risk_factors=risk_factors,
        bullish_factors=bullish_factors,
        bearish_factors=bearish_factors,
        all_items=items,
    )
