"""Base adapter interface that every source adapter must implement."""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from research.models import NormalizedItem, SourceCategory, SourceType
from research.source_catalog import SourceMeta, get_source_meta

logger = logging.getLogger(__name__)


class AdapterResult:
    """Container for adapter fetch results with observability metadata."""

    def __init__(self, source_key: str):
        self.source_key = source_key
        self.items: list[NormalizedItem] = []
        self.fetch_success: bool = False
        self.parse_errors: int = 0
        self.fetch_latency_ms: float = 0
        self.rate_limited: bool = False
        self.empty_response: bool = False
        self.error = None  # str or None

    def to_dict(self) -> dict:
        return {
            "source": self.source_key,
            "items_count": len(self.items),
            "fetch_success": self.fetch_success,
            "parse_errors": self.parse_errors,
            "fetch_latency_ms": round(self.fetch_latency_ms, 1),
            "rate_limited": self.rate_limited,
            "empty_response": self.empty_response,
            "error": self.error,
        }


class SourceAdapter(ABC):
    """Interface for a data source adapter.

    Subclasses must implement:
      - fetch()   → raw data from the source
      - parse()   → list of extracted dicts
      - normalize() → list of NormalizedItem
      - score()   → items with trust/influence scores set
    """

    source_key: str = ""  # must match a key in SOURCE_CATALOG

    def __init__(self):
        self.meta = get_source_meta(self.source_key)

    # ── abstract methods ───────────────────────────────────

    @abstractmethod
    def fetch(self) -> Any:
        """Fetch raw data from the source. Return raw payload."""
        ...

    @abstractmethod
    def parse(self, raw: Any) -> list[dict]:
        """Parse raw payload into a list of intermediate dicts."""
        ...

    @abstractmethod
    def normalize(self, parsed: list[dict]) -> list[NormalizedItem]:
        """Convert parsed dicts into NormalizedItem instances."""
        ...

    def score(self, items: list[NormalizedItem]) -> list[NormalizedItem]:
        """Apply trust and influence scores. Default uses source reliability."""
        base = self.meta.reliability if self.meta else 0.5
        for item in items:
            item.trust_score = base
            # Boost primary sources, penalize opinion
            if item.source_type == SourceType.PRIMARY:
                item.trust_score = min(1.0, item.trust_score + 0.1)
            elif item.source_type == SourceType.OPINION:
                item.trust_score = max(0.0, item.trust_score - 0.15)
            # Freshness boost: items < 1 hour old get a bump
            if item.published_at:
                age_hours = (datetime.utcnow() - item.published_at).total_seconds() / 3600
                if age_hours < 1:
                    item.influence_score += 0.2
                elif age_hours < 6:
                    item.influence_score += 0.1
        return items

    # ── orchestration ──────────────────────────────────────

    def run(self) -> AdapterResult:
        """Full pipeline: fetch → parse → normalize → score, with logging.

        Each stage is isolated so a partial failure (e.g. one bad item during
        parsing) doesn't discard the items that were already processed
        successfully.
        """
        result = AdapterResult(self.source_key)
        t0 = time.time()

        # ── fetch ──────────────────────────────────────────
        try:
            raw = self.fetch()
            result.fetch_success = True
        except Exception as e:
            result.error = f"fetch failed: {e}"
            logger.error(f"[{self.source_key}] fetch error: {e}", exc_info=True)
            result.fetch_latency_ms = (time.time() - t0) * 1000
            return result

        if not raw:
            result.empty_response = True
            logger.warning(f"[{self.source_key}] empty response")
            result.fetch_latency_ms = (time.time() - t0) * 1000
            return result

        # ── parse ──────────────────────────────────────────
        parsed: list[dict] = []
        try:
            parsed = self.parse(raw)
        except Exception as e:
            result.error = f"parse failed: {e}"
            result.parse_errors += 1
            logger.error(f"[{self.source_key}] parse error: {e}", exc_info=True)

        # ── normalize (item-level isolation) ───────────────
        items: list[NormalizedItem] = []
        for i, entry in enumerate(parsed):
            try:
                normalized = self._normalize_single(entry)
                items.extend(normalized)
            except Exception as e:
                result.parse_errors += 1
                logger.warning(
                    f"[{self.source_key}] failed to normalize item {i}: {e}"
                )

        # ── score ──────────────────────────────────────────
        try:
            items = self.score(items)
        except Exception as e:
            logger.error(f"[{self.source_key}] scoring error: {e}", exc_info=True)
            # items keep their default scores — still usable

        result.items = items
        result.fetch_latency_ms = (time.time() - t0) * 1000
        logger.info(
            f"[{self.source_key}] fetched {len(result.items)} items "
            f"({result.parse_errors} parse errors) "
            f"in {result.fetch_latency_ms:.0f}ms"
        )
        return result

    def _normalize_single(self, entry: dict) -> list[NormalizedItem]:
        """Normalize a single parsed entry. Wraps the subclass normalize()
        call so it can be used per-item for isolation."""
        return self.normalize([entry])
