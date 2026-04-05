"""Simple TTL-based in-memory cache for research data."""
from __future__ import annotations

import time
import threading
from typing import Any, Optional


class TTLCache:
    """Thread-safe in-memory cache with per-key TTL."""

    def __init__(self):
        self._store: dict[str, tuple[Any, float]] = {}  # key → (value, expires_at)
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.time() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        with self._lock:
            self._store[key] = (value, time.time() + ttl_seconds)

    def invalidate(self, key: str):
        with self._lock:
            self._store.pop(key, None)

    def clear(self):
        with self._lock:
            self._store.clear()

    def stats(self) -> dict:
        with self._lock:
            now = time.time()
            total = len(self._store)
            expired = sum(1 for _, (_, exp) in self._store.items() if now > exp)
            return {"total_keys": total, "expired": expired, "active": total - expired}


# Singleton cache instance
research_cache = TTLCache()

# Recommended TTLs by data type (seconds)
CACHE_TTLS = {
    "macro_series": 3600,       # 1 hour — macro data doesn't change fast
    "company_profiles": 7200,   # 2 hours
    "filings_metadata": 1800,   # 30 min
    "news_headlines": 300,      # 5 min — news is time-sensitive
    "narrative_clusters": 600,  # 10 min
    "market_report": 600,       # 10 min
}
