"""Alpha Vantage adapter — market data and news sentiment.

Requires ALPHA_VANTAGE_KEY (free tier: 25 req/day).
https://www.alphavantage.co/documentation/
"""
from __future__ import annotations

import logging
import os
from datetime import datetime

import requests

from research.models import NormalizedItem, SourceCategory, SourceType, SentimentDirection
from research.adapters.base import SourceAdapter

logger = logging.getLogger(__name__)

AV_KEY = os.getenv("ALPHA_VANTAGE_KEY", "")
AV_BASE = "https://www.alphavantage.co/query"


class AlphaVantageNewsAdapter(SourceAdapter):
    """Fetches news sentiment from Alpha Vantage NEWS_SENTIMENT endpoint."""
    source_key = "alpha_vantage"

    def __init__(self, tickers: list[str] | None = None, topics: list[str] | None = None):
        super().__init__()
        if tickers:
            self.tickers = tickers
        else:
            import config as _cfg
            self.tickers = list(_cfg.INSTRUMENTS.keys())[:10]
        self.topics = topics or [
            "economy_macro", "financial_markets", "technology",
            "energy_transportation",
        ]
        self._session = requests.Session()

    def fetch(self) -> dict:
        if not AV_KEY:
            logger.warning("[alpha_vantage] ALPHA_VANTAGE_KEY not set — skipping")
            return {}

        results: dict[str, list] = {"news": []}

        # News sentiment — one call covers multiple tickers/topics
        try:
            params = {
                "function": "NEWS_SENTIMENT",
                "tickers": ",".join(self.tickers[:5]),
                "topics": ",".join(self.topics[:3]),
                "sort": "LATEST",
                "limit": 20,
                "apikey": AV_KEY,
            }
            resp = self._session.get(AV_BASE, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()

            if "Note" in data or "Information" in data:
                logger.warning(f"[alpha_vantage] API limit: {data.get('Note') or data.get('Information')}")
                return results

            results["news"] = data.get("feed", [])[:20]
        except Exception as e:
            logger.error(f"[alpha_vantage] news sentiment error: {e}")

        return results

    def parse(self, raw: dict) -> list[dict]:
        parsed = []
        for item in raw.get("news", []):
            ticker_sentiments = item.get("ticker_sentiment", [])
            symbols = [ts.get("ticker", "") for ts in ticker_sentiments if ts.get("ticker")]

            # Aggregate sentiment from ticker-level scores
            scores = []
            for ts in ticker_sentiments:
                try:
                    scores.append(float(ts.get("ticker_sentiment_score", 0)))
                except (ValueError, TypeError):
                    pass
            avg_score = sum(scores) / len(scores) if scores else 0

            parsed.append({
                "title": item.get("title", ""),
                "summary": item.get("summary", ""),
                "url": item.get("url", ""),
                "source": item.get("source", ""),
                "time_published": item.get("time_published", ""),
                "overall_sentiment_score": item.get("overall_sentiment_score", 0),
                "overall_sentiment_label": item.get("overall_sentiment_label", "Neutral"),
                "ticker_sentiment_avg": avg_score,
                "symbols": symbols,
                "topics": [t.get("topic", "") for t in item.get("topics", [])],
            })
        return parsed

    def normalize(self, parsed: list[dict]) -> list[NormalizedItem]:
        items = []
        for p in parsed:
            pub = None
            ts = p.get("time_published", "")
            if ts:
                try:
                    pub = datetime.strptime(ts[:15], "%Y%m%dT%H%M%S")
                except (ValueError, TypeError):
                    pass

            # Map AV sentiment label to our enum
            label = p.get("overall_sentiment_label", "Neutral").lower()
            if "bullish" in label:
                sentiment = SentimentDirection.BULLISH
            elif "bearish" in label:
                sentiment = SentimentDirection.BEARISH
            else:
                sentiment = SentimentDirection.NEUTRAL

            items.append(NormalizedItem(
                title=p.get("title", ""),
                summary=p.get("summary", "")[:500],
                source="alpha_vantage",
                category=SourceCategory.NEWS,
                source_type=SourceType.SECONDARY,
                published_at=pub,
                url=p.get("url", ""),
                symbols=p.get("symbols", []),
                regions=["US"],
                themes=p.get("topics", []),
                sentiment=sentiment,
                raw_payload={"av_sentiment_score": p.get("overall_sentiment_score", 0)},
            ))
        return items
