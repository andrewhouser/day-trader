"""Finviz adapter — market sentiment via RSS news feed.

Finviz provides a public RSS feed for market news. No API key required.
We use the RSS feed (not scraping) to stay within legal boundaries.
"""
from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime

import requests

from research.models import NormalizedItem, SourceCategory, SourceType, SentimentDirection
from research.adapters.base import SourceAdapter

logger = logging.getLogger(__name__)

FINVIZ_RSS = "https://finviz.com/news_export.ashx?v=3"


class FinvizAdapter(SourceAdapter):
    """Fetches market news headlines from Finviz RSS feed."""
    source_key = "finviz"

    def __init__(self):
        super().__init__()
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "TraderResearchAgent/1.0"

    def fetch(self) -> str | None:
        try:
            resp = self._session.get(FINVIZ_RSS, timeout=15)
            if resp.status_code == 403:
                logger.warning("[finviz] access denied (403) — may need browser headers")
                return None
            if resp.status_code == 429:
                logger.warning("[finviz] rate limited")
                return None
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            logger.error(f"[finviz] fetch error: {e}")
            return None

    def parse(self, raw: str | None) -> list[dict]:
        if not raw:
            return []
        parsed = []
        try:
            root = ET.fromstring(raw)
            for item in root.findall(".//item"):
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                pub_date = item.findtext("pubDate", "")
                description = item.findtext("description", "")
                parsed.append({
                    "title": title,
                    "link": link,
                    "pub_date": pub_date,
                    "description": description,
                })
        except ET.ParseError as e:
            logger.error(f"[finviz] XML parse error: {e}")
        return parsed[:30]

    def normalize(self, parsed: list[dict]) -> list[NormalizedItem]:
        items = []
        for p in parsed:
            pub = None
            pd_str = p.get("pub_date", "")
            if pd_str:
                for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S"]:
                    try:
                        pub = datetime.strptime(pd_str.strip(), fmt)
                        if pub.tzinfo:
                            pub = pub.replace(tzinfo=None)
                        break
                    except ValueError:
                        continue

            # Simple keyword-based sentiment hint
            title_lower = (p.get("title", "") + " " + p.get("description", "")).lower()
            sentiment = SentimentDirection.NEUTRAL
            bullish_kw = ["surge", "rally", "gain", "jump", "rise", "bull", "record high", "beat"]
            bearish_kw = ["drop", "fall", "crash", "plunge", "sell", "bear", "miss", "cut", "fear"]
            bull_hits = sum(1 for kw in bullish_kw if kw in title_lower)
            bear_hits = sum(1 for kw in bearish_kw if kw in title_lower)
            if bull_hits > bear_hits:
                sentiment = SentimentDirection.BULLISH
            elif bear_hits > bull_hits:
                sentiment = SentimentDirection.BEARISH

            # Extract ticker-like symbols from title
            symbols = re.findall(r'\b([A-Z]{2,5})\b', p.get("title", ""))
            # Filter to likely tickers (crude heuristic)
            common_words = {"THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL",
                            "CAN", "HER", "WAS", "ONE", "OUR", "OUT", "NEW", "HAS",
                            "ITS", "SAY", "WHO", "HOW", "NOW", "MAY", "CEO", "IPO",
                            "GDP", "CPI", "FED", "SEC", "ETF", "USD", "EUR"}
            symbols = [s for s in symbols if s not in common_words][:5]

            items.append(NormalizedItem(
                title=p.get("title", ""),
                summary=p.get("description", "")[:300] or p.get("title", ""),
                source="finviz",
                category=SourceCategory.SENTIMENT,
                source_type=SourceType.SECONDARY,
                published_at=pub,
                url=p.get("link", ""),
                symbols=symbols,
                regions=["US"],
                themes=["market_news"],
                sentiment=sentiment,
            ))
        return items
