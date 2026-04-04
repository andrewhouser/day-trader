"""Performance analyst agent: runs weekly to compute quantitative
metrics from trade history and write a performance report."""
import json
import logging
import re
from datetime import datetime

import config
from agent import append_to_file, call_ollama, load_portfolio, read_recent_entries

logger = logging.getLogger(__name__)

PERFORMANCE_SYSTEM = (
    "You are a quantitative trading performance analyst. You compute metrics "
    "from trade data and produce actionable insights. Be precise with numbers. "
    "Identify patterns in wins and losses. Compare performance across instruments."
)


def _parse_all_trades() -> list[dict]:
    """Parse all trades from trade_log.md into structured dicts."""
    try:
        with open(config.TRADE_LOG_PATH, "r") as f:
            content = f.read()
    except FileNotFoundError:
        return []

    sections = content.split("\n---\n")
    trades = []

    for section in sections[1:]:
        section = section.strip()
        if not section or "No Action" in section.split("\n")[0]:
            continue
        if "Trade Rejected" in section.split("\n")[0]:
            continue

        trade: dict = {}
        for line in section.split("\n"):
            line = line.strip().lstrip("- ")
            if line.startswith("**Date:**"):
                trade["date"] = line.replace("**Date:**", "").strip()
            elif line.startswith("**Action:**"):
                trade["action"] = line.replace("**Action:**", "").strip()
            elif line.startswith("**Instrument:**"):
                trade["instrument"] = line.replace("**Instrument:**", "").strip()
            elif line.startswith("**Quantity:**"):
                try:
                    trade["quantity"] = float(line.replace("**Quantity:**", "").strip())
                except ValueError:
                    pass
            elif line.startswith("**Price:**"):
                price_str = line.replace("**Price:**", "").strip().replace("$", "")
                try:
                    trade["price"] = float(price_str)
                except ValueError:
                    pass
            elif line.startswith("**Realized P&L:**"):
                pnl_str = line.replace("**Realized P&L:**", "").strip().replace("$", "")
                try:
                    trade["realized_pnl"] = float(pnl_str)
                except ValueError:
                    pass
            elif line.startswith("**Entry Scores:**"):
                scores_str = line.replace("**Entry Scores:**", "").strip()
                try:
                    trade["entry_scores"] = json.loads(scores_str)
                except (json.JSONDecodeError, ValueError):
                    pass

        if trade.get("action") in ("BUY", "SELL"):
            trades.append(trade)

    return trades


def _compute_metrics(trades: list[dict], portfolio: dict) -> dict:
    """Compute quantitative performance metrics."""
    if not trades:
        return {"total_trades": 0}

    buys = [t for t in trades if t.get("action") == "BUY"]
    sells = [t for t in trades if t.get("action") == "SELL"]
    realized_trades = [t for t in sells if "realized_pnl" in t]

    wins = [t for t in realized_trades if t["realized_pnl"] > 0]
    losses = [t for t in realized_trades if t["realized_pnl"] < 0]
    breakeven = [t for t in realized_trades if t["realized_pnl"] == 0]

    total_realized_pnl = sum(t["realized_pnl"] for t in realized_trades)
    avg_win = sum(t["realized_pnl"] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t["realized_pnl"] for t in losses) / len(losses) if losses else 0

    # Per-instrument breakdown
    by_instrument: dict[str, dict] = {}
    for t in realized_trades:
        inst = t.get("instrument", "Unknown").split("(")[0].strip()
        if inst not in by_instrument:
            by_instrument[inst] = {"trades": 0, "pnl": 0, "wins": 0, "losses": 0}
        by_instrument[inst]["trades"] += 1
        by_instrument[inst]["pnl"] += t["realized_pnl"]
        if t["realized_pnl"] > 0:
            by_instrument[inst]["wins"] += 1
        elif t["realized_pnl"] < 0:
            by_instrument[inst]["losses"] += 1

    # Compute holding periods and per-trade P&L %
    trade_details = _compute_trade_details(trades)

    gain_loss = portfolio["total_value_usd"] - portfolio["starting_capital"]
    pct_return = (gain_loss / portfolio["starting_capital"]) * 100

    return {
        "total_trades": len(trades),
        "total_buys": len(buys),
        "total_sells": len(sells),
        "realized_trades": len(realized_trades),
        "wins": len(wins),
        "losses": len(losses),
        "breakeven": len(breakeven),
        "win_rate": round(len(wins) / len(realized_trades) * 100, 1) if realized_trades else 0,
        "total_realized_pnl": round(total_realized_pnl, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(abs(avg_win / avg_loss), 2) if avg_loss != 0 else float("inf"),
        "portfolio_value": portfolio["total_value_usd"],
        "starting_capital": portfolio["starting_capital"],
        "total_return_pct": round(pct_return, 2),
        "all_time_high": portfolio["all_time_high"],
        "all_time_low": portfolio["all_time_low"],
        "max_drawdown_from_ath": round(
            ((portfolio["all_time_high"] - portfolio["all_time_low"]) / portfolio["all_time_high"]) * 100, 2
        ) if portfolio["all_time_high"] > 0 else 0,
        "by_instrument": by_instrument,
        "trade_details": trade_details,
    }


def _compute_trade_details(trades: list[dict]) -> dict:
    """Compute per-trade details: holding periods, P&L %, direction accuracy.
    Matches BUY/SELL pairs per instrument to compute round-trip stats."""
    from datetime import datetime as dt

    open_positions: dict[str, list] = {}
    closed_trades: list[dict] = []

    for t in trades:
        inst = t.get("instrument", "Unknown").split("(")[0].strip()
        action = t.get("action", "")
        date_str = t.get("date", "")
        price = t.get("price", 0)
        quantity = t.get("quantity", 0)

        try:
            trade_date = dt.strptime(date_str, "%Y-%m-%d %H:%M:%S") if date_str else None
        except ValueError:
            trade_date = None

        if action == "BUY":
            if inst not in open_positions:
                open_positions[inst] = []
            open_positions[inst].append({"date": trade_date, "price": price, "quantity": quantity})

        elif action == "SELL" and inst in open_positions and open_positions[inst]:
            entry = open_positions[inst][0]  # FIFO
            entry_date = entry["date"]
            entry_price = entry["price"]

            holding_hours = None
            if entry_date and trade_date:
                holding_hours = round((trade_date - entry_date).total_seconds() / 3600, 1)

            pnl_pct = ((price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
            is_win = pnl_pct > 0

            closed_trades.append({
                "instrument": inst,
                "entry_price": entry_price,
                "exit_price": price,
                "pnl_pct": round(pnl_pct, 2),
                "holding_hours": holding_hours,
                "is_win": is_win,
                "realized_pnl": t.get("realized_pnl", 0),
            })

            # Remove or reduce the open position
            if quantity >= entry["quantity"]:
                open_positions[inst].pop(0)
            else:
                entry["quantity"] -= quantity

    if not closed_trades:
        return {"closed_count": 0, "patterns": []}

    wins = [ct for ct in closed_trades if ct["is_win"]]
    losses = [ct for ct in closed_trades if not ct["is_win"]]

    avg_win_hold = sum(ct["holding_hours"] for ct in wins if ct["holding_hours"] is not None) / len(wins) if wins else None
    avg_loss_hold = sum(ct["holding_hours"] for ct in losses if ct["holding_hours"] is not None) / len(losses) if losses else None
    avg_win_pct = sum(ct["pnl_pct"] for ct in wins) / len(wins) if wins else 0
    avg_loss_pct = sum(ct["pnl_pct"] for ct in losses) / len(losses) if losses else 0

    best_trade = max(closed_trades, key=lambda x: x["pnl_pct"]) if closed_trades else None
    worst_trade = min(closed_trades, key=lambda x: x["pnl_pct"]) if closed_trades else None

    # Detect patterns
    patterns = []
    if avg_win_hold is not None and avg_loss_hold is not None:
        if avg_win_hold < avg_loss_hold * 0.5:
            patterns.append(
                f"You tend to sell winners too early (avg hold: {avg_win_hold:.1f}h) "
                f"and hold losers too long (avg hold: {avg_loss_hold:.1f}h)"
            )
        elif avg_loss_hold < avg_win_hold * 0.5:
            patterns.append(
                f"Good discipline: cutting losses quickly (avg hold: {avg_loss_hold:.1f}h) "
                f"and letting winners run (avg hold: {avg_win_hold:.1f}h)"
            )

    if avg_win_pct > 0 and abs(avg_loss_pct) > avg_win_pct * 2:
        patterns.append(
            f"Risk/reward imbalance: avg win is {avg_win_pct:.1f}% but avg loss is {avg_loss_pct:.1f}%. "
            f"Consider tighter stops or larger profit targets."
        )

    return {
        "closed_count": len(closed_trades),
        "avg_win_hold_hours": round(avg_win_hold, 1) if avg_win_hold else None,
        "avg_loss_hold_hours": round(avg_loss_hold, 1) if avg_loss_hold else None,
        "avg_win_pct": round(avg_win_pct, 2),
        "avg_loss_pct": round(avg_loss_pct, 2),
        "best_trade": best_trade,
        "worst_trade": worst_trade,
        "last_5_trades": closed_trades[-5:],
        "patterns": patterns,
    }


def run_performance_analysis() -> str:
    """Run the weekly performance analysis."""
    logger.info("Starting weekly performance analysis...")

    portfolio = load_portfolio()
    trades = _parse_all_trades()
    metrics = _compute_metrics(trades, portfolio)
    recent_reflections = read_recent_entries(config.REFLECTIONS_PATH, 10)

    # Read lessons if available
    try:
        with open(config.LESSONS_PATH, "r") as f:
            lessons = f.read()[-2000:]
    except FileNotFoundError:
        lessons = "No lessons file yet."

    prompt = f"""Weekly Performance Analysis

### Quantitative Metrics
```json
{json.dumps(metrics, indent=2)}
```

### Recent Reflections
{recent_reflections}

### Existing Lessons
{lessons}

---

Produce a comprehensive performance report with these sections:

1. **Performance Summary**
   - Total return, win rate, profit factor
   - Comparison to a simple buy-and-hold of SPY over the same period

2. **Trade Analysis**
   - Average hold time (estimate from dates if possible)
   - Best and worst trades
   - Most and least profitable instruments

3. **Pattern Recognition**
   - Are there patterns in winning vs losing trades?
   - Time-of-day or day-of-week patterns?
   - Does the agent trade too frequently or not enough?

4. **Risk Assessment**
   - Max drawdown analysis
   - Position sizing effectiveness
   - Were stop-losses triggered appropriately?

5. **Recommendations**
   - 3-5 specific, actionable recommendations to improve performance
   - Each should reference specific data from the metrics above

Be quantitative. Use the actual numbers. Don't be vague."""

    logger.info("Sending performance analysis prompt to LLM...")
    response = call_ollama(prompt, system=PERFORMANCE_SYSTEM, model=config.RESEARCH_MODEL, timeout=config.RESEARCH_TIMEOUT)

    # Retry once if the first attempt failed (Ollama may have been loading the model)
    if response.startswith("[ERROR]"):
        logger.warning("First performance LLM call failed, retrying...")
        response = call_ollama(prompt, system=PERFORMANCE_SYSTEM, model=config.RESEARCH_MODEL, timeout=config.RESEARCH_TIMEOUT)

    logger.info(f"Performance analysis received ({len(response)} chars)")

    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    # Save to performance.md
    try:
        with open(config.PERFORMANCE_PATH, "r"):
            pass
    except FileNotFoundError:
        with open(config.PERFORMANCE_PATH, "w") as f:
            f.write("# Performance Reports\n\nWeekly quantitative performance analysis.\n\n---\n")

    entry = f"""
## Performance Report - {timestamp}

### Raw Metrics
```json
{json.dumps(metrics, indent=2)}
```

### Analysis
{response}

---
"""
    append_to_file(config.PERFORMANCE_PATH, entry)

    # Also save a dated report
    report_path = f"{config.REPORTS_DIR}/{now.strftime('%Y-%m-%d')}_performance.md"
    with open(report_path, "w") as f:
        f.write(f"# Performance Report - {now.strftime('%Y-%m-%d')}\n\n")
        f.write(f"```json\n{json.dumps(metrics, indent=2)}\n```\n\n")
        f.write(response)

    logger.info(f"Performance report saved to {report_path}")

    # Update adaptive score weights from closed trades with entry_scores
    try:
        from score_weights import update_weights_from_outcome
        weight_updates = 0
        for t in trades:
            if t.get("action") != "SELL" or "realized_pnl" not in t:
                continue
            # Parse entry_scores from the trade log if present
            inst = t.get("instrument", "Unknown").split("(")[0].strip()
            entry_scores = t.get("entry_scores")
            if entry_scores:
                update_weights_from_outcome(inst, entry_scores, t["realized_pnl"])
                weight_updates += 1
        if weight_updates:
            logger.info(f"Updated score weights from {weight_updates} closed trade(s)")
    except Exception as e:
        logger.warning(f"Score weight update failed: {e}")

    return response


def get_performance_feedback() -> str:
    """Generate a concise performance feedback string for the hourly trading prompt.
    Includes win rate, patterns, and last 5 trades."""
    try:
        portfolio = load_portfolio()
        trades = _parse_all_trades()
        metrics = _compute_metrics(trades, portfolio)
    except Exception as e:
        logger.debug(f"Could not generate performance feedback: {e}")
        return "No performance data available yet."

    if metrics.get("total_trades", 0) == 0:
        return "No trades executed yet — no performance data."

    lines = []

    # Summary stats
    win_rate = metrics.get("win_rate", 0)
    avg_win = metrics.get("avg_win", 0)
    avg_loss = metrics.get("avg_loss", 0)
    total_return = metrics.get("total_return_pct", 0)
    realized = metrics.get("realized_trades", 0)

    lines.append(f"Total return: {total_return:+.2f}% | Win rate: {win_rate:.1f}% ({realized} closed trades)")
    lines.append(f"Avg win: ${avg_win:.2f} | Avg loss: ${avg_loss:.2f} | Profit factor: {metrics.get('profit_factor', 'N/A')}")

    # Trade details and patterns
    details = metrics.get("trade_details", {})
    if details.get("closed_count", 0) > 0:
        if details.get("avg_win_hold_hours") is not None:
            lines.append(
                f"Avg hold (wins): {details['avg_win_hold_hours']}h | "
                f"Avg hold (losses): {details.get('avg_loss_hold_hours', 'N/A')}h"
            )
        if details.get("avg_win_pct"):
            lines.append(f"Avg win %: {details['avg_win_pct']}% | Avg loss %: {details.get('avg_loss_pct', 0)}%")

        # Patterns
        for pattern in details.get("patterns", []):
            lines.append(f"⚠️ PATTERN: {pattern}")

        # Best/worst trade
        best = details.get("best_trade")
        worst = details.get("worst_trade")
        if best:
            lines.append(f"Best trade: {best['instrument']} ({best['pnl_pct']:+.1f}%)")
        if worst:
            lines.append(f"Worst trade: {worst['instrument']} ({worst['pnl_pct']:+.1f}%)")

        # Last 5 trades
        last5 = details.get("last_5_trades", [])
        if last5:
            lines.append("Last 5 closed trades:")
            for t in last5:
                emoji = "✅" if t["is_win"] else "❌"
                hold = f"{t['holding_hours']}h" if t.get("holding_hours") else "?"
                lines.append(
                    f"  {emoji} {t['instrument']}: {t['pnl_pct']:+.1f}% "
                    f"(${t.get('realized_pnl', 0):.2f}) held {hold}"
                )

    return "\n".join(lines)
