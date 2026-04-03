"""Adaptive score dimension weights — learns from trade outcomes to adjust
which scoring dimensions matter most for each instrument."""
import json
import logging
import os

import config

logger = logging.getLogger(__name__)

WEIGHTS_PATH = os.path.join(config.DATA_DIR, "score_weights.json")

DEFAULT_WEIGHTS = {
    "trend": 1.0,
    "momentum": 1.0,
    "sentiment": 1.0,
    "risk_reward": 1.0,
    "event_risk": 1.0,
    "sector_divergence": 1.0,
}

WEIGHT_MIN = 0.5
WEIGHT_MAX = 2.0
NUDGE = 0.05


def _load_all() -> dict:
    """Load the full weights file."""
    try:
        with open(WEIGHTS_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_all(data: dict) -> None:
    """Persist the full weights file."""
    with open(WEIGHTS_PATH, "w") as f:
        json.dump(data, f, indent=2)


def load_weights(ticker: str) -> dict:
    """Return dimension weights for ticker, falling back to DEFAULT_WEIGHTS."""
    all_weights = _load_all()
    return all_weights.get(ticker, dict(DEFAULT_WEIGHTS))


def save_weights(ticker: str, weights: dict) -> None:
    """Persist updated weights for ticker to score_weights.json."""
    all_weights = _load_all()
    all_weights[ticker] = weights
    _save_all(all_weights)


def compute_weighted_composite(scores: dict, ticker: str) -> float:
    """Apply per-instrument weights to raw scores and return weighted composite."""
    weights = load_weights(ticker)
    total = 0.0
    for dim, raw_score in scores.items():
        if dim == "composite":
            continue
        w = weights.get(dim, 1.0)
        total += raw_score * w
    return round(total, 2)


def update_weights_from_outcome(ticker: str, entry_scores: dict, outcome_pnl: float) -> None:
    """Nudge weights toward dimensions that predicted the outcome correctly.

    - Win (pnl > 0): boost dimensions that scored >= +1, reduce those <= -1
    - Loss (pnl < 0): reduce dimensions that scored >= +1, boost those <= -1
    - Clamp all weights to [WEIGHT_MIN, WEIGHT_MAX]
    """
    weights = load_weights(ticker)
    is_win = outcome_pnl > 0

    for dim in DEFAULT_WEIGHTS:
        score = entry_scores.get(dim)
        if score is None:
            continue
        if is_win:
            if score >= 1:
                weights[dim] = min(weights.get(dim, 1.0) + NUDGE, WEIGHT_MAX)
            elif score <= -1:
                weights[dim] = max(weights.get(dim, 1.0) - NUDGE, WEIGHT_MIN)
        else:
            if score >= 1:
                weights[dim] = max(weights.get(dim, 1.0) - NUDGE, WEIGHT_MIN)
            elif score <= -1:
                weights[dim] = min(weights.get(dim, 1.0) + NUDGE, WEIGHT_MAX)

    save_weights(ticker, weights)
    logger.info(f"Updated weights for {ticker}: {weights}")


def get_weights_summary() -> str:
    """Return a human-readable table of current weights for all instruments."""
    all_weights = _load_all()
    if not all_weights:
        return "No learned weights yet — all dimensions weighted equally at 1.0."

    dims = list(DEFAULT_WEIGHTS.keys())
    header = f"{'Ticker':<8} " + " ".join(f"{d:<18}" for d in dims)
    lines = [header, "-" * len(header)]

    for ticker in sorted(all_weights.keys()):
        w = all_weights[ticker]
        vals = " ".join(f"{w.get(d, 1.0):<18.2f}" for d in dims)
        lines.append(f"{ticker:<8} {vals}")

    return "\n".join(lines)
