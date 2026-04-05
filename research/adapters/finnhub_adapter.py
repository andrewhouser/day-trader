"""Finnhub adapter — market news and company news via free API.

Requires FINNHUB_API_KEY (free tier: 60 calls/min).
https://finnhub.io/docs/api
"""
from __future__ import annotations

import logging
import os
from datetime import datetime

import requests

from research.models import NormalizedItem, SourceCategory, SourceType, SentimentDirection
from research.adapters.base import SourceAdapter

logger = logging.getLogger(__name__)

FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "")
FINNHUB_BASE = "https://finnhub.io/api/v1"


class FinnhubNewsAdapter(SourceAdapter):
    """Fetches general and company-specific market news from Finnhub."""
    source_key = "finnhub"

    def __init__(self, symbols: list[str] | None = None):
        super().__init__()
        if symbols:
            self.symbols = symbols
        else:
            import config as _cfg
            self.symbols = list(_cfg.INSTRUMENTS.keys())[:10]  # Top 10 instruments
        self._session = requests.Session()

    def fetch(self) -> dict:
        if not FINNHUB_KEY:
            logger.warning("[finnhub] FINNHUB_API_KEY not set — skipping")
            return {}

        results: dict[str, list] = {"general": [], "company": []}

        # General market news
        try:
            resp = self._session.get(
                f"{FINNHUB_BASE}/news",
                params={"category": "general", "token": FINNHUB_KEY},
                timeout=15,
            )
            if resp.status_code == 429:
                logger.warning("[finnhub] rate limited on general news")
            else:
                resp.raise_for_status()
                results["general"] = resp.json()[:20]
        except Exception as e:
            logger.error(f"[finnhub] general news error: {e}")

        # Company news for key symbols
        today = datetime.utcnow().strftime("%Y-%m-%d")
        for sym in self.symbols[:6]:  # limit to avoid rate limits
            try:
                resp = self._session.get(
                    f"{FINNHUB_BASE}/company-news",
                    params={
                        "symbol": sym,
                        "from": today,
                        "to": today,
                        "token": FINNHUB_KEY,
                    },
                    timeout=15,
                )
                if resp.status_code == 429:
                    logger.warning(f"[finnhub] rate limited on {sym}")
                    break
                resp.raise_for_status()
                news = resp.json()[:5]
                for item in news:
                    item["_symbol"] = sym
                results["company"].extend(news)
            except Exception as e:
                logger.error(f"[finnhub] company news error for {sym}: {e}")

        return results

    def parse(self, raw: dict) -> list[dict]:
        parsed = []
        seen_ids = set()

        for item in raw.get("general", []):
            item_id = item.get("id", item.get("url", ""))
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            parsed.append({
                "headline": item.get("headline", ""),
                "summary": item.get("summary", ""),
                "source": item.get("source", ""),
                "url": item.get("url", ""),
                "datetime": item.get("datetime", 0),
                "category": item.get("category", "general"),
                "related": item.get("related", ""),
                "symbol": None,
                "is_company": False,
            })

        for item in raw.get("company", []):
            item_id = item.get("id", item.get("url", ""))
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            parsed.append({
                "headline": item.get("headline", ""),
                "summary": item.get("summary", ""),
                "source": item.get("source", ""),
                "url": item.get("url", ""),
                "datetime": item.get("datetime", 0),
                "category": item.get("category", "company"),
                "related": item.get("related", ""),
                "symbol": item.get("_symbol"),
                "is_company": True,
            })

        return parsed

    def normalize(self, parsed: list[dict]) -> list[NormalizedItem]:
        items = []
        for p in parsed:
            pub = None
            ts = p.get("datetime", 0)
            if ts:
                try:
                    pub = datetime.utcfromtimestamp(ts)
                except (OSError, ValueError):
                    pass

            symbols = []
            if p.get("symbol"):
                symbols.append(p["symbol"])
            related = p.get("related", "")
            if related:
                symbols.extend([s.strip() for s in related.split(",") if s.strip()])

            items.append(NormalizedItem(
                title=p.get("headline", ""),
                summary=p.get("summary", "")[:500],
                source="finnhub",
                category=SourceCategory.NEWS,
                source_type=SourceType.SECONDARY,
                published_at=pub,
                url=p.get("url", ""),
                symbols=list(set(symbols)),
                regions=["US"],
                themes=["company" if p.get("is_company") else "market"],
            ))
        return items
