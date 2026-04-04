"""Strategy score ladder: classifies trades by strategy type and tracks per-strategy
win/loss statistics so the trading agent can see which approaches are working."""
import json
import logging
import re
from datetime import datetime
from pathlib import Path

import config

logger = logging.getLogger(__name__)

# ── Strategy taxonomy ─────────────────────────────────────────────────────────
# Each entry defines keyword signals used to classify a trade entry's reasoning
# text.  Classification is done with a simple keyword-priority scan; the first
# matching category wins.  More specific categories should appear earlier.

STRATEGY_DEFINITIONS: dict[str, dict] = {
    "vix_spike_rotation": {
        "display": "VIX Spike / Safe-Haven Rotation",
        "keywords": ["vix spike", "vix >", "volatility spike", "safe haven", "flight to safety",
                     "fear index", "high volatility regime", "risk-off"],
        "description": "Rotating to safe havens (GLD, TLT, SHY) when VIX spikes or fear dominates",
    },
    "sector_rotation": {
        "display": "Sector Rotation",
        "keywords": ["sector rotation", "rotate into", "rotate out", "defensive sector",
                     "cyclical sector", "regime shift", "regime change", "xlp", "xlu", "xlk", "xlf"],
        "description": "Rotating between sectors in response to regime or macro shifts",
    },
    "momentum_continuation": {
        "display": "Momentum Continuation",
        "keywords": ["momentum", "continuation", "breakout", "trend continuation",
                     "strong uptrend", "strong trend", "bullish momentum", "rsi above 60",
                     "macd positive", "accelerating"],
        "description": "Buying into an established, confirmed uptrend with strong momentum",
    },
    "mean_reversion": {
        "display": "Mean Reversion",
        "keywords": ["mean reversion", "oversold", "rsi below 30", "rsi < 30", "bounce",
                     "support level", "lower bollinger", "stretched to the downside",
                     "overextended down", "capitulation"],
        "description": "Buying deeply oversold instruments expecting a bounce to the mean",
    },
    "sector_divergence": {
        "display": "Sector Divergence",
        "keywords": ["divergence", "diverging", "independent of spy", "counter-cyclical",
                     "moving independently", "against the market", "decoupled",
                     "fundamental driver", "supply shock", "geopolitical"],
        "description": "Trading an instrument moving independently of the broad market with a clear driver",
    },
    "contrarian_breakout": {
        "display": "Contrarian / Breakout",
        "keywords": ["contrarian", "breakout", "resistance break", "new high", "52-week",
                     "all-time high", "breakout above", "volume surge"],
        "description": "Entering on a high-conviction breakout against prevailing sentiment",
    },
    "event_catalyst": {
        "display": "Event Catalyst",
        "keywords": ["earnings", "fomc", "fed decision", "cpi", "nfp", "jobs report",
                     "economic release", "catalyst", "event-driven", "before the report",
                     "ahead of earnings"],
        "description": "Positioning for or around a known scheduled catalyst",
    },
    "stop_management": {
        "display": "Stop / Risk Management Exit",
        "keywords": ["stop loss", "trailing stop", "stop triggered", "risk management",
                     "exit to manage risk", "cut the loss", "position too large",
                     "reduce exposure", "drawdown"],
        "description": "Selling to enforce stop-loss or risk management rules (not a strategy, but tracked)",
    },
    "take_profit": {
        "display": "Take-Profit / Target Exit",
        "keywords": ["take profit", "target reached", "take gains", "partial profit",
                     "lock in gains", "selling into strength", "+5%", "+8%", "profit target"],
        "description": "Selling to lock in gains at a target level",
    },
}

# Ordered list for priority matching (more specific first)
_STRATEGY_ORDER = list(STRATEGY_DEFINITIONS.keys())

_DEFAULT_SCORES: dict = {
    name: {
        "display": defn["display"],
        "description": defn["description"],
        "wins": 0,
        "losses": 0,
        "neutral": 0,
        "total": 0,
        "win_rate": None,
        "avg_pnl_pct": None,
        "total_pnl": 0.0,
        "suspended": False,
        "last_updated": None,
    }
    for name, defn in STRATEGY_DEFINITIONS.items()
}


def _load_scores() -> dict:
    try:
        with open(config.STRATEGY_SCORES_PATH, "r") as f:
            stored = json.load(f)
        # Merge any new strategy keys that may have been added since last save
        for name, default in _DEFAULT_SCORES.items():
            if name not in stored:
                stored[name] = dict(default)
        return stored
    except (FileNotFoundError, json.JSONDecodeError):
        return {name: dict(d) for name, d in _DEFAULT_SCORES.items()}


def _save_scores(scores: dict):
    with open(config.STRATEGY_SCORES_PATH, "w") as f:
        json.dump(scores, f, indent=2)


def classify_trade_strategy(reasoning: str) -> str:
    """Classify a trade into a strategy category based on its reasoning text.

    Returns the category key (e.g. 'momentum_continuation') or 'unclassified'.
    """
    text = reasoning.lower()
    for name in _STRATEGY_ORDER:
        defn = STRATEGY_DEFINITIONS[name]
        for kw in defn["keywords"]:
            if kw in text:
                return name
    return "unclassified"


def update_strategy_scores(
    strategy: str,
    realized_pnl: float,
    entry_price: float,
    quantity: int,
) -> dict:
    """Record the outcome of a closed trade for the given strategy.

    Args:
        strategy:     Strategy key from classify_trade_strategy().
        realized_pnl: Dollar P&L of the closed trade.
        entry_price:  Original entry price (used to compute % P&L).
        quantity:     Shares traded (for cost basis).

    Returns updated scores dict.
    """
    scores = _load_scores()

    if strategy not in scores:
        scores[strategy] = {
            "display": strategy,
            "description": "User-defined or auto-detected strategy",
            "wins": 0,
            "losses": 0,
            "neutral": 0,
            "total": 0,
            "win_rate": None,
            "avg_pnl_pct": None,
            "total_pnl": 0.0,
            "suspended": False,
            "last_updated": None,
        }

    entry = scores[strategy]
    cost_basis = entry_price * quantity if entry_price and quantity else 1
    pnl_pct = (realized_pnl / cost_basis) * 100 if cost_basis else 0

    if realized_pnl > 0.01:
        entry["wins"] += 1
    elif realized_pnl < -0.01:
        entry["losses"] += 1
    else:
        entry["neutral"] += 1

    entry["total"] += 1
    entry["total_pnl"] = round(entry.get("total_pnl", 0.0) + realized_pnl, 2)

    if entry["total"] > 0:
        entry["win_rate"] = round(entry["wins"] / entry["total"], 3)
        # Rolling avg P&L % (approximate via cumulative total / count)
        entry["avg_pnl_pct"] = round(pnl_pct, 2)   # single-trade update; playbook does full recalc

    entry["last_updated"] = datetime.now().isoformat()

    # Auto-suspend strategies that have ≥10 trades and win rate < 35%
    min_trades = 10
    suspend_threshold = 0.35
    if entry["total"] >= min_trades and entry["win_rate"] is not None:
        entry["suspended"] = entry["win_rate"] < suspend_threshold

    _save_scores(scores)
    logger.info(
        f"Strategy '{strategy}' updated: {entry['wins']}W/{entry['losses']}L "
        f"({entry['win_rate']*100:.0f}% win rate) total_pnl=${entry['total_pnl']:.2f}"
    )
    return scores


def get_strategy_ladder() -> str:
    """Return a markdown table of all strategies with their performance stats.

    Suspended strategies are flagged. Strategies with no trades are omitted
    unless they have a non-zero count.
    """
    scores = _load_scores()

    active_rows = []
    suspended_rows = []

    for name, entry in scores.items():
        if entry.get("total", 0) == 0:
            continue
        win_rate_str = f"{entry['win_rate']*100:.0f}%" if entry.get("win_rate") is not None else "—"
        pnl_str = f"${entry.get('total_pnl', 0):+.2f}"
        status = "⛔ SUSPENDED" if entry.get("suspended") else "✓ Active"
        row = (
            f"| {entry.get('display', name):<38} | "
            f"{entry.get('wins', 0):>4}W / {entry.get('losses', 0):>4}L / {entry.get('neutral', 0):>3}N | "
            f"{win_rate_str:>8} | {pnl_str:>12} | {status} |"
        )
        if entry.get("suspended"):
            suspended_rows.append(row)
        else:
            active_rows.append(row)

    if not active_rows and not suspended_rows:
        return "\n### Strategy Score Ladder\nNo closed trades recorded yet.\n"

    header = (
        "\n### Strategy Score Ladder\n"
        "| Strategy                                | W / L / N     | Win Rate |     Total P&L | Status      |\n"
        "|-----------------------------------------|---------------|----------|---------------|-------------|"
    )
    rows = active_rows + suspended_rows
    footer = (
        "\nSuspended strategies (⛔) have ≥10 trades and win rate <35%. "
        "The trading agent should avoid them until market conditions change."
    )
    return header + "\n" + "\n".join(rows) + "\n" + footer


def get_suspended_strategies() -> list[str]:
    """Return a list of currently suspended strategy display names."""
    scores = _load_scores()
    return [
        entry.get("display", name)
        for name, entry in scores.items()
        if entry.get("suspended", False)
    ]
