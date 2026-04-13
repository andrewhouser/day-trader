"""Rolling 30-day market context: computes and caches a structured summary of
recent regime transitions, instrument performance, correlation structure, and
agent performance so the trading agent always carries 30-day institutional memory."""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import config

logger = logging.getLogger(__name__)

_CONTEXT_HEADER = """# Rolling 30-Day Market Context

Auto-generated context window.  Updated daily at 6:55 AM ET before market open.
The trading agent reads this every cycle as a compact historical summary.

---
"""


def _load_portfolio_history(days: int = 30) -> list[dict]:
    """Load portfolio history snapshots for the last N days."""
    try:
        with open(config.PORTFOLIO_HISTORY_PATH, "r") as f:
            history = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    cutoff = datetime.now() - timedelta(days=days)
    recent = []
    for snap in history:
        try:
            ts = datetime.fromisoformat(snap["timestamp"])
            if ts >= cutoff:
                recent.append(snap)
        except (ValueError, KeyError):
            continue
    return recent


def _parse_recent_trades(days: int = 30) -> list[dict]:
    """Parse trade_log.md for trades in the last N days."""
    import re

    try:
        with open(config.TRADE_LOG_PATH, "r") as f:
            content = f.read()
    except FileNotFoundError:
        return []

    cutoff = datetime.now() - timedelta(days=days)
    trades = []
    sections = content.split("\n---\n")

    for section in sections:
        if not section.strip():
            continue
        date_match = re.search(r"\*\*Date:\*\*\s*([\d]{4}-[\d]{2}-[\d]{2})", section)
        if not date_match:
            continue
        try:
            trade_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
        except ValueError:
            continue
        if trade_date < cutoff:
            continue

        action_match = re.search(r"^## (BUY|SELL|NO[_ ]ACTION)", section, re.MULTILINE)
        if not action_match:
            continue

        ticker_match = re.search(r"\*\*Instrument:\*\*\s*(\w+)", section)
        pnl_match = re.search(r"\*\*Realized P&L:\*\*\s*\$([-]?\d+\.?\d*)\b", section)

        trades.append({
            "date": date_match.group(1),
            "action": action_match.group(1),
            "ticker": ticker_match.group(1).strip() if ticker_match else "",
            "realized_pnl": float(pnl_match.group(1)) if pnl_match else None,
        })

    return trades


def _parse_regime_transitions(days: int = 30) -> list[str]:
    """Extract regime change notes from reflections.md."""
    import re

    try:
        with open(config.REFLECTIONS_PATH, "r") as f:
            content = f.read()
    except FileNotFoundError:
        return []

    cutoff = datetime.now() - timedelta(days=days)
    transitions = []
    sections = content.split("\n---\n")

    for section in sections:
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", section)
        if not date_match:
            continue
        try:
            entry_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
        except ValueError:
            continue
        if entry_date < cutoff:
            continue

        # Look for regime mentions
        regime_match = re.search(
            r"\*\*Regime:\*\*\s*(STRONG_UPTREND|UPTREND|SIDEWAYS|DOWNTREND|STRONG_DOWNTREND|HIGH_VOLATILITY)",
            section,
        )
        if regime_match:
            transitions.append(f"{date_match.group(1)}: {regime_match.group(1)}")

    # Deduplicate consecutive same-regime entries, keep only transitions
    deduped = []
    last = None
    for t in transitions:
        regime = t.split(": ", 1)[1] if ": " in t else t
        if regime != last:
            deduped.append(t)
            last = regime

    return deduped[-10:]  # last 10 regime transitions max


def _compute_instrument_performance(trades: list[dict]) -> dict[str, dict]:
    """Compute win/loss + total P&L per instrument from recent closed trades."""
    perf: dict[str, dict] = {}
    for t in trades:
        if t["action"] != "SELL" or t.get("realized_pnl") is None:
            continue
        sym = t["ticker"]
        if sym not in perf:
            perf[sym] = {"wins": 0, "losses": 0, "total_pnl": 0.0}
        p = perf[sym]
        p["total_pnl"] = round(p["total_pnl"] + t["realized_pnl"], 2)
        if t["realized_pnl"] > 0.01:
            p["wins"] += 1
        elif t["realized_pnl"] < -0.01:
            p["losses"] += 1
    return perf


def update_market_context(days: int = 30) -> str:
    """Compute and write a fresh 30-day market context summary to market_context.md.

    Called by the scheduler each morning and on demand via API.
    Returns the generated context text.
    """
    logger.info("Updating 30-day market context...")
    now = datetime.now()

    # Portfolio value arc
    history = _load_portfolio_history(days)
    portfolio_arc = ""
    if history:
        start_val = history[0]["total_value_usd"]
        end_val = history[-1]["total_value_usd"]
        change = end_val - start_val
        change_pct = (change / start_val * 100) if start_val else 0
        peak = max(s["total_value_usd"] for s in history)
        trough = min(s["total_value_usd"] for s in history)
        max_dd = ((peak - trough) / peak * 100) if peak else 0
        portfolio_arc = (
            f"- {days}d change: ${start_val:.2f} → ${end_val:.2f} "
            f"({change_pct:+.2f}%)\n"
            f"- Period high: ${peak:.2f} | Period low: ${trough:.2f}\n"
            f"- Max intra-period drawdown: {max_dd:.1f}%"
        )
    else:
        portfolio_arc = "- No portfolio history available yet."

    # Regime transitions
    transitions = _parse_regime_transitions(days)
    regime_section = "\n".join(f"  {t}" for t in transitions) if transitions else "  No regime changes recorded."

    # Trade stats
    trades = _parse_recent_trades(days)
    closed = [t for t in trades if t["action"] == "SELL" and t.get("realized_pnl") is not None]
    total_realized = sum(t["realized_pnl"] for t in closed if t["realized_pnl"] is not None)
    wins = sum(1 for t in closed if t.get("realized_pnl", 0) > 0.01)
    losses = sum(1 for t in closed if t.get("realized_pnl", 0) < -0.01)
    win_rate = f"{wins/(wins+losses)*100:.0f}%" if (wins + losses) > 0 else "N/A"

    # Best/worst instruments
    inst_perf = _compute_instrument_performance(trades)
    sorted_inst = sorted(inst_perf.items(), key=lambda x: x[1]["total_pnl"], reverse=True)
    best = [(sym, d) for sym, d in sorted_inst if d["total_pnl"] > 0][:3]
    worst = [(sym, d) for sym, d in sorted_inst if d["total_pnl"] < 0][-3:]

    best_str = ", ".join(f"{sym} (+${d['total_pnl']:.2f})" for sym, d in best) if best else "None"
    worst_str = ", ".join(f"{sym} (-${abs(d['total_pnl']):.2f})" for sym, d in worst) if worst else "None"

    # Correlation structure note (lightweight — just reads current state)
    try:
        from market_data import fetch_correlation_matrix
        corr = fetch_correlation_matrix(lookback_days=min(days, 20))
        high_pairs = corr.get("high_correlation_pairs", [])
        if high_pairs:
            corr_note = ", ".join(f"{a}↔{b}(r={c:+.2f})" for a, b, c in high_pairs[:5])
        else:
            corr_note = "No high-correlation pairs — portfolio well-diversified"
    except Exception:
        corr_note = "Correlation data unavailable"

    # Strategy ladder summary
    strategy_section = ""
    try:
        from strategy_tracker import get_strategy_ladder
        strategy_section = get_strategy_ladder()
    except Exception:
        strategy_section = "Strategy scores unavailable."

    context = f"""{_CONTEXT_HEADER}*Generated: {now.strftime('%Y-%m-%d %H:%M:%S')} | Window: last {days} days*

## Portfolio Arc ({days}d)
{portfolio_arc}

## Regime Transitions (chronological)
{regime_section}

## Trade Statistics ({days}d)
- Closed trades: {len(closed)} ({wins}W / {losses}L / win rate {win_rate})
- Total realized P&L: ${total_realized:+.2f}
- Best instruments: {best_str}
- Worst instruments: {worst_str}

## Correlation Structure (recent)
{corr_note}

{strategy_section}
"""

    with open(config.MARKET_CONTEXT_PATH, "w") as f:
        f.write(context)

    logger.info(f"Market context written to {config.MARKET_CONTEXT_PATH}")
    return context


def get_market_context_for_prompt() -> str:
    """Read market_context.md for injection into the hourly trading prompt.

    Falls back to computing a fresh context if the file doesn't exist yet.
    """
    try:
        with open(config.MARKET_CONTEXT_PATH, "r") as f:
            return f.read()
    except FileNotFoundError:
        logger.info("market_context.md not found — computing on-demand")
        try:
            return update_market_context()
        except Exception as exc:
            logger.warning(f"On-demand market context failed: {exc}")
            return "Rolling market context not yet available."
