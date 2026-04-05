"""Investing.com adapter — market news via RSS feeds.

Investing.com provides public RSS feeds for news. No API key required.
We use RSS feeds only (not scraping) to stay within legal boundaries.
"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime

import requests

from research.models import NormalizedItem, SourceCategory, SourceType, SentimentDirection
from research.adapters.base import SourceAdapter

logger = logging.getLogger(__name__)

INVESTING_FEEDS = {
    "news": "https://www.investing.com/rss/news.rss",
    "market_overview": "https://www.investing.com/rss/market_overview.rss",
    "forex": "https://www.investing.com/rss/forex.rss",
    "commodities": "https://www.investing.com/rss/commodities.rss",
}


class InvestingComAdapter(SourceAdapter):
    """Fetches market news from Investing.com RSS feeds."""
    source_key = "investing_com"

    def __init__(self, feeds: dict[str, str] | None = None):
        super().__init__()
        self.feeds = feeds or INVESTING_FEEDS
        self._session = requests.Session()
        self._session.headers["User-Agent"] = (
            "Mozilla/5.0 (compatible; TraderResearchAgent/1.0)"
        )

    def fetch(self) -> dict[str, str]:
        results = {}
        for name, url in self.feeds.items():
            try:
                resp = self._session.get(url, timeout=15)
                if resp.status_code in (403, 429):
                    logger.warning(f"[investing_com] {resp.status_code} on {name}")
                    continue
                resp.raise_for_status()
                results[name] = resp.text
            except Exception as e:
                logger.error(f"[investing_com] error fetching {name}: {e}")
        return results

    def parse(self, raw: dict[str, str]) -> list[dict]:
        parsed = []
        seen = set()
        for feed_name, xml_text in raw.items():
            if not xml_text:
                continue
            try:
                root = ET.fromstring(xml_text)
                for item in root.findall(".//item"):
                    title = item.findtext("title", "").strip()
                    if not title or title in seen:
                        continue
                    seen.add(title)
                    parsed.append({
                        "title": title,
                        "link": item.findtext("link", "").strip(),
                        "pub_date": item.findtext("pubDate", "").strip(),
                        "description": item.findtext("description", "").strip(),
                        "feed": feed_name,
                    })
            except ET.ParseError as e:
                logger.error(f"[investing_com] XML parse error on {feed_name}: {e}")
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

            # Map feed to region/theme
            feed = p.get("feed", "news")
            themes = [feed]
            regions = ["GLOBAL"]
            if feed == "forex":
                themes.append("fx")
            elif feed == "commodities":
                themes.append("commodities")

            items.append(NormalizedItem(
                title=p.get("title", ""),
                summary=p.get("description", "")[:500] or p.get("title", ""),
                source="investing_com",
                category=SourceCategory.NEWS,
                source_type=SourceType.SECONDARY,
                published_at=pub,
                url=p.get("link", ""),
                symbols=[],
                regions=regions,
                themes=themes,
            ))
        return items
