"""Tests for adapter base class and mocked adapter behavior."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime
from research.adapters.base import SourceAdapter, AdapterResult
from research.models import NormalizedItem, SourceCategory, SourceType


class MockAdapter(SourceAdapter):
    """A mock adapter for testing the base class pipeline."""
    source_key = "yfinance"  # use an existing catalog entry

    def __init__(self, raw_data=None, should_fail=False):
        super().__init__()
        self._raw = [{"headline": "Test headline"}] if raw_data is None else raw_data
        self._should_fail = should_fail

    def fetch(self):
        if self._should_fail:
            raise ConnectionError("Mock connection error")
        return self._raw

    def parse(self, raw):
        return [{"title": item.get("headline", "")} for item in raw]

    def normalize(self, parsed):
        return [
            NormalizedItem(
                title=p["title"],
                source="yfinance",
                category=SourceCategory.MARKET_DATA,
                source_type=SourceType.SECONDARY,
                published_at=datetime.utcnow(),
            )
            for p in parsed
        ]


def test_adapter_run_success():
    adapter = MockAdapter()
    result = adapter.run()
    assert result.fetch_success is True
    assert len(result.items) == 1
    assert result.items[0].title == "Test headline"
    assert result.error is None
    assert result.fetch_latency_ms > 0


def test_adapter_run_failure():
    adapter = MockAdapter(should_fail=True)
    result = adapter.run()
    assert result.fetch_success is False
    assert len(result.items) == 0
    assert result.error is not None
    assert "Mock connection error" in result.error


def test_adapter_run_empty():
    adapter = MockAdapter(raw_data=[])
    result = adapter.run()
    assert result.fetch_success is True
    assert len(result.items) == 0


def test_adapter_scoring():
    adapter = MockAdapter()
    result = adapter.run()
    # yfinance has reliability 0.70 in catalog
    assert result.items[0].trust_score >= 0.5


def test_adapter_result_to_dict():
    result = AdapterResult("test_source")
    result.fetch_success = True
    result.fetch_latency_ms = 123.456
    d = result.to_dict()
    assert d["source"] == "test_source"
    assert d["fetch_success"] is True
    assert d["fetch_latency_ms"] == 123.5


class PartialFailAdapter(SourceAdapter):
    """Adapter where normalize() blows up on one specific item."""
    source_key = "yfinance"

    def __init__(self):
        super().__init__()

    def fetch(self):
        return [{"headline": "Good item"}, {"headline": "Bad item"}, {"headline": "Also good"}]

    def parse(self, raw):
        return [{"title": item["headline"]} for item in raw]

    def normalize(self, parsed):
        results = []
        for p in parsed:
            if p["title"] == "Bad item":
                raise ValueError("Simulated normalize failure")
            results.append(
                NormalizedItem(
                    title=p["title"],
                    source="yfinance",
                    category=SourceCategory.MARKET_DATA,
                    source_type=SourceType.SECONDARY,
                )
            )
        return results


def test_adapter_partial_normalize_failure():
    """If one item fails to normalize, the others should still come through."""
    adapter = PartialFailAdapter()
    result = adapter.run()
    assert result.fetch_success is True
    # 3 items parsed, 1 fails normalize → 2 survive
    assert len(result.items) == 2
    assert result.parse_errors == 1
    titles = [item.title for item in result.items]
    assert "Good item" in titles
    assert "Also good" in titles
    assert "Bad item" not in titles
