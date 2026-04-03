"""Tests for the TTL cache."""
import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from research.cache import TTLCache


def test_cache_set_get():
    cache = TTLCache()
    cache.set("key1", "value1", ttl_seconds=60)
    assert cache.get("key1") == "value1"


def test_cache_miss():
    cache = TTLCache()
    assert cache.get("nonexistent") is None


def test_cache_expiry():
    cache = TTLCache()
    cache.set("key1", "value1", ttl_seconds=1)
    time.sleep(1.1)
    assert cache.get("key1") is None


def test_cache_invalidate():
    cache = TTLCache()
    cache.set("key1", "value1", ttl_seconds=60)
    cache.invalidate("key1")
    assert cache.get("key1") is None


def test_cache_clear():
    cache = TTLCache()
    cache.set("a", 1, ttl_seconds=60)
    cache.set("b", 2, ttl_seconds=60)
    cache.clear()
    assert cache.get("a") is None
    assert cache.get("b") is None


def test_cache_stats():
    cache = TTLCache()
    cache.set("a", 1, ttl_seconds=60)
    cache.set("b", 2, ttl_seconds=60)
    stats = cache.stats()
    assert stats["total_keys"] == 2
    assert stats["active"] == 2
