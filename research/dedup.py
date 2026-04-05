"""Deduplication — remove near-duplicate items based on title similarity."""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from research.models import NormalizedItem


def _clean(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def deduplicate(
    items: list[NormalizedItem],
    threshold: float = 0.75,
) -> list[NormalizedItem]:
    """Remove near-duplicate items. When duplicates are found, keep the one
    with the higher trust_score (preferring primary sources)."""
    if not items:
        return []

    kept: list[NormalizedItem] = []
    cleaned_titles: list[str] = []

    # Sort by trust_score descending so higher-trust items are kept first
    sorted_items = sorted(items, key=lambda x: x.trust_score, reverse=True)

    for item in sorted_items:
        clean_title = _clean(item.title)
        if not clean_title:
            kept.append(item)
            cleaned_titles.append("")
            continue

        is_dup = False
        for existing_title in cleaned_titles:
            if not existing_title:
                continue
            if _similarity(clean_title, existing_title) >= threshold:
                is_dup = True
                break

        if not is_dup:
            kept.append(item)
            cleaned_titles.append(clean_title)

    return kept
