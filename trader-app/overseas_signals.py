"""Overseas trade signal queue.

Overseas monitors (Nikkei, FTSE) write structured trade signals here when
they detect significant moves in international markets.  The U.S. trading
agent consumes these signals during its next hourly check, evaluating them
alongside its normal scoring framework before deciding whether to act.

Signal lifecycle:
  1. Monitor detects a significant move → calls emit_signal()
  2. Signal is written to overseas_signals.json with status "pending"
  3. U.S. hourly check reads pending signals via get_pending_signals()
  4. After evaluation, the agent marks signals as "evaluated" via
     mark_signals_evaluated()
  5. Stale signals (older than OVERSEAS_SIGNAL_MAX_AGE_HOURS) are
     automatically pruned on every read.
"""
import json
import logging
import os
import tempfile
from datetime import datetime, timedelta

import config

logger = logging.getLogger(__name__)


def _load_signals() -> list[dict]:
    try:
        with open(config.OVERSEAS_SIGNALS_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_signals(signals: list[dict]):
    """Write signals atomically."""
    try:
        dir_path = os.path.dirname(config.OVERSEAS_SIGNALS_PATH)
        with tempfile.NamedTemporaryFile(
            mode="w", dir=dir_path, suffix=".tmp", delete=False
        ) as f:
            json.dump(signals, f, indent=2, default=str)
            tmp_path = f.name
        os.replace(tmp_path, config.OVERSEAS_SIGNALS_PATH)
    except Exception as e:
        logger.error(f"Failed to save overseas signals: {e}")


def _prune_stale(signals: list[dict]) -> list[dict]:
    """Remove signals older than the configured max age."""
    cutoff = datetime.now() - timedelta(hours=config.OVERSEAS_SIGNAL_MAX_AGE_HOURS)
    kept = []
    for s in signals:
        try:
            ts = datetime.fromisoformat(s["timestamp"])
            if ts >= cutoff:
                kept.append(s)
            else:
                logger.debug(f"Pruning stale signal: {s.get('ticker')} from {s['timestamp']}")
        except (KeyError, ValueError):
            kept.append(s)  # keep malformed entries for manual inspection
    return kept


def emit_signal(
    source: str,
    ticker: str,
    direction: str,
    move_pct: float,
    driver: str,
    urgency: str = "normal",
    suggested_action: str = "",
) -> dict:
    """Write a trade signal from an overseas monitor.

    Args:
        source: Which monitor emitted this ("nikkei_open", "nikkei_reopen",
                "ftse_open", "europe_handoff").
        ticker: The U.S.-listed ETF to consider (e.g. "EWJ", "EWU", "EWG").
        direction: "bullish" or "bearish".
        move_pct: The magnitude of the overseas move that triggered this signal.
        driver: One-sentence explanation of the fundamental driver.
        urgency: "high" (act at next opportunity) or "normal" (evaluate normally).
        suggested_action: Optional — "BUY", "SELL", or "" (let the trader decide).

    Returns:
        The signal dict that was written.
    """
    signal = {
        "id": f"{source}_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "source": source,
        "ticker": ticker,
        "direction": direction,
        "move_pct": round(move_pct, 2),
        "driver": driver,
        "urgency": urgency,
        "suggested_action": suggested_action,
        "status": "pending",
        "timestamp": datetime.now().isoformat(),
        "evaluated_at": None,
    }

    signals = _load_signals()
    signals = _prune_stale(signals)
    signals.append(signal)
    _save_signals(signals)

    logger.info(
        f"Overseas signal emitted: {direction.upper()} {ticker} "
        f"({move_pct:+.2f}%) from {source} — {driver}"
    )
    return signal


def get_pending_signals() -> list[dict]:
    """Return all pending (unevaluated) signals, pruning stale ones."""
    signals = _load_signals()
    signals = _prune_stale(signals)
    _save_signals(signals)  # persist the pruning
    return [s for s in signals if s.get("status") == "pending"]


def mark_signals_evaluated(signal_ids: list[str]):
    """Mark signals as evaluated after the U.S. agent has processed them."""
    signals = _load_signals()
    now = datetime.now().isoformat()
    updated = 0
    for s in signals:
        if s.get("id") in signal_ids and s.get("status") == "pending":
            s["status"] = "evaluated"
            s["evaluated_at"] = now
            updated += 1
    _save_signals(signals)
    if updated:
        logger.info(f"Marked {updated} overseas signal(s) as evaluated")


def format_signals_for_prompt(signals: list[dict]) -> str:
    """Format pending signals into a readable block for the trading prompt."""
    if not signals:
        return ""

    lines = ["### 🌏 Overseas Trade Signals (pending evaluation)", ""]
    for s in signals:
        urgency_tag = "🔴 HIGH URGENCY" if s.get("urgency") == "high" else "🟡 Normal"
        action_hint = f" → Suggested: {s['suggested_action']}" if s.get("suggested_action") else ""
        lines.append(
            f"- **{s['ticker']}** ({s['direction'].upper()}, {s['move_pct']:+.2f}%) "
            f"[{urgency_tag}]{action_hint}\n"
            f"  Source: {s['source']} at {s['timestamp'][:16]}\n"
            f"  Driver: {s['driver']}"
        )
    lines.append("")
    lines.append(
        "**INSTRUCTIONS:** Evaluate each signal using the standard scoring framework. "
        "Overseas signals provide an informational edge — they are NOT automatic trades. "
        "Apply the same composite score thresholds, position sizing, and risk rules. "
        "High-urgency signals should be evaluated first but still require a passing score."
    )
    return "\n".join(lines)
