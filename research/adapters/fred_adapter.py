"""FRED (Federal Reserve Economic Data) adapter.

Uses the public FRED API (requires free API key from https://fred.stlouisfed.org/docs/api/).
Fetches key macro series: GDP, CPI, unemployment, fed funds rate, etc.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta

import requests

from research.models import NormalizedItem, SourceCategory, SourceType, SentimentDirection
from research.adapters.base import SourceAdapter

logger = logging.getLogger(__name__)

FRED_API_KEY = os.getenv("FRED_API_KEY", "")
FRED_BASE = "https://api.stlouisfed.org/fred"

# Key macro series to track
FRED_SERIES = {
    "GDP": {"id": "GDP", "name": "Real GDP", "theme": "growth"},
    "UNRATE": {"id": "UNRATE", "name": "Unemployment Rate", "theme": "labor"},
    "CPIAUCSL": {"id": "CPIAUCSL", "name": "CPI (All Urban Consumers)", "theme": "inflation"},
    "FEDFUNDS": {"id": "FEDFUNDS", "name": "Federal Funds Rate", "theme": "rates"},
    "T10Y2Y": {"id": "T10Y2Y", "name": "10Y-2Y Treasury Spread", "theme": "rates"},
    "DGS10": {"id": "DGS10", "name": "10-Year Treasury Yield", "theme": "rates"},
    "DTWEXBGS": {"id": "DTWEXBGS", "name": "Trade-Weighted Dollar Index", "theme": "fx"},
    "ICSA": {"id": "ICSA", "name": "Initial Jobless Claims", "theme": "labor"},
    "UMCSENT": {"id": "UMCSENT", "name": "Consumer Sentiment (UMich)", "theme": "sentiment"},
    "VIXCLS": {"id": "VIXCLS", "name": "VIX", "theme": "volatility"},
}


class FredAdapter(SourceAdapter):
    source_key = "fred"

    def __init__(self, series_ids: list[str] | None = None):
        super().__init__()
        self.series_ids = series_ids or list(FRED_SERIES.keys())
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "TraderResearchAgent/1.0"

    def fetch(self) -> list[dict]:
        if not FRED_API_KEY:
            logger.warning("[fred] FRED_API_KEY not set — skipping")
            return []

        results = []
        end = datetime.utcnow().strftime("%Y-%m-%d")
        start = (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%d")

        for sid in self.series_ids:
            try:
                url = (
                    f"{FRED_BASE}/series/observations"
                    f"?series_id={sid}&api_key={FRED_API_KEY}"
                    f"&file_type=json&sort_order=desc&limit=5"
                    f"&observation_start={start}&observation_end={end}"
                )
                resp = self._session.get(url, timeout=15)
                if resp.status_code == 429:
                    logger.warning(f"[fred] rate limited on {sid}")
                    continue
                resp.raise_for_status()
                data = resp.json()
                obs = data.get("observations", [])
                if obs:
                    results.append({"series_id": sid, "observations": obs})
            except Exception as e:
                logger.error(f"[fred] error fetching {sid}: {e}")
        return results

    def parse(self, raw: list[dict]) -> list[dict]:
        parsed = []
        for entry in raw:
            sid = entry["series_id"]
            obs = entry.get("observations", [])
            if not obs:
                continue
            meta = FRED_SERIES.get(sid, {"name": sid, "theme": "macro"})
            latest = obs[0]
            prev = obs[1] if len(obs) > 1 else None

            val = latest.get("value", ".")
            prev_val = prev.get("value", ".") if prev else "."

            parsed.append({
                "series_id": sid,
                "name": meta["name"],
                "theme": meta["theme"],
                "date": latest.get("date", ""),
                "value": val,
                "prev_value": prev_val,
            })
        return parsed

    def normalize(self, parsed: list[dict]) -> list[NormalizedItem]:
        items = []
        for p in parsed:
            val_str = p["value"]
            prev_str = p["prev_value"]
            try:
                val = float(val_str)
                prev = float(prev_str) if prev_str != "." else None
                if prev:
                    change = val - prev
                    direction = "up" if change > 0 else "down" if change < 0 else "flat"
                    summary = f"{p['name']}: {val} ({direction} from {prev})"
                else:
                    summary = f"{p['name']}: {val}"
            except (ValueError, TypeError):
                summary = f"{p['name']}: {val_str}"

            pub_date = None
            try:
                pub_date = datetime.strptime(p["date"], "%Y-%m-%d")
            except (ValueError, TypeError):
                pass

            items.append(NormalizedItem(
                title=f"FRED: {p['name']} update",
                summary=summary,
                source="fred",
                category=SourceCategory.MACRO,
                source_type=SourceType.PRIMARY,
                published_at=pub_date,
                url=f"https://fred.stlouisfed.org/series/{p['series_id']}",
                symbols=[],
                regions=["US"],
                themes=[p["theme"], "macro"],
                raw_payload=p,
            ))
        return items
