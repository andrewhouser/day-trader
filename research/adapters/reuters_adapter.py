"""Reuters adapter — market news via Reuters RSS feeds.

Reuters provides public RSS feeds for various news categories.
No API key required. We use RSS (not scraping) to stay within legal boundaries.
"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime

import requests

from research.models import NormalizedItem, SourceCategory, SourceType, SentimentDirection
from research.adapters.base import SourceAdapter

logger = logging.getLogger(__name__)

# Reuters RSS feeds — publicly available
REUTERS_FEEDS = {
    "business": "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
    "markets": "https://www.reutersagency.com/feed/?best-topics=economy&post_type=best",
}


class ReutersAdapter(SourceAdapter):
    """Fetches market/business news from Reuters RSS feeds."""
    source_key = "reuters"

    def __init__(self, feeds: dict[str, str] | None = None):
        super().__init__()
        self.feeds = feeds or REUTERS_FEEDS
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "TraderResearchAgent/1.0"

    def fetch(self) -> dict[str, str]:
        results = {}
        for name, url in self.feeds.items():
            try:
                resp = self._session.get(url, timeout=15)
                if resp.status_code == 403:
                    logger.warning(f"[reuters] 403 on {name} feed — may be geo-blocked")
                    continue
                if resp.status_code == 429:
                    logger.warning(f"[reuters] rate limited on {name}")
                    continue
                resp.raise_for_status()
                results[name] = resp.text
            except Exception as e:
                logger.error(f"[reuters] error fetching {name}: {e}")
        return results

    def parse(self, raw: dict[str, str]) -> list[dict]:
        parsed = []
        seen_titles = set()
        for feed_name, xml_text in raw.items():
            if not xml_text:
                continue
            try:
                root = ET.fromstring(xml_text)
                for item in root.findall(".//item"):
                    title = item.findtext("title", "").strip()
                    if not title or title in seen_titles:
                        continue
                    seen_titles.add(title)
                    parsed.append({
                        "title": title,
                        "link": item.findtext("link", "").strip(),
                        "pub_date": item.findtext("pubDate", "").strip(),
                        "description": item.findtext("description", "").strip(),
                        "feed": feed_name,
                    })
            except ET.ParseError as e:
                logger.error(f"[reuters] XML parse error on {feed_name}: {e}")
        return parsed[:25]

    def normalize(self, parsed: list[dict]) -> list[NormalizedItem]:
        items = []
        for p in parsed:
            pub = None
            pd_str = p.get("pub_date", "")
            if pd_str:
                for fmt in [
                    "%a, %d %b %Y %H:%M:%S %z",
                    "%a, %d %b %Y %H:%M:%S %Z",
                    "%a, %d %b %Y %H:%M:%S",
                ]:
                    try:
                        pub = datetime.strptime(pd_str.strip(), fmt)
                        if pub.tzinfo:
                            pub = pub.replace(tzinfo=None)
                        break
                    except ValueError:
                        continue

            # Determine region from content
            title_lower = p.get("title", "").lower()
            regions = ["GLOBAL"]
            region_hints = {
                "US": ["fed ", "u.s.", "wall street", "nasdaq", "s&p", "dow"],
                "EU": ["ecb", "euro", "europe", "eu "],
                "UK": ["boe", "britain", "uk ", "ftse", "london"],
                "ASIA": ["boj", "japan", "china", "nikkei", "hang seng", "asia"],
            }
            for region, keywords in region_hints.items():
                if any(kw in title_lower for kw in keywords):
                    regions.append(region)

            items.append(NormalizedItem(
                title=p.get("title", ""),
                summary=p.get("description", "")[:500] or p.get("title", ""),
                source="reuters",
                category=SourceCategory.NEWS,
                source_type=SourceType.SECONDARY,
                published_at=pub,
                url=p.get("link", ""),
                symbols=[],
                regions=regions,
                themes=[p.get("feed", "general")],
            ))
        return items
