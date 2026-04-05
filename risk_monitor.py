"""Risk monitor agent: runs on a tight loop to watch for stop-loss
breaches, volatility spikes, correlation concentration, portfolio
drawdown, trailing stop breaches, and take-profit targets.
Executes automatic sells for trailing stops and take-profits."""
import json
import logging
from datetime import datetime

import config
from agent import append_to_file, call_ollama, execute_trade, load_portfolio, save_portfolio, run_hourly_check
from market_data import fetch_instrument_prices, fetch_technical_indicators

logger = logging.getLogger(__name__)


def _check_drawdown(portfolio: dict) -> dict | None:
    """Check if portfolio has drawn down beyond threshold from ATH."""
    ath = portfolio.get("all_time_high", portfolio["starting_capital"])
    current = portfolio["total_value_usd"]
    if ath <= 0:
        return None
    drawdown_pct = ((ath - current) / ath) * 100
    if drawdown_pct >= config.RISK_MAX_DRAWDOWN_PCT:
        return {
            "type": "drawdown",
            "ath": ath,
            "current": current,
            "drawdown_pct": round(drawdown_pct, 2),
        }
    return None


def _check_volatility(instruments: dict) -> list[dict]:
    """Flag instruments with high intraday swings."""
    alerts = []
    for ticker, data in instruments.items():
        if "error" in data:
            continue
        high = data.get("high", 0)
        low = data.get("low", 0)
        if low <= 0:
            continue
        intraday_range_pct = ((high - low) / low) * 100
        if intraday_range_pct >= config.RISK_VOLATILITY_THRESHOLD:
            alerts.append({
                "type": "volatility",
                "ticker": ticker,
                "high": high,
                "low": low,
                "range_pct": round(intraday_range_pct, 2),
                "current_price": data.get("price", 0),
            })
    return alerts


def _check_correlation(portfolio: dict, instruments: dict) -> dict | None:
    """Check if all positions are moving in the same direction (concentration risk)."""
    positions = portfolio.get("positions", [])
    if len(positions) < 2:
        return None

    directions = []
    for pos in positions:
        ticker = pos["ticker"]
        data = instruments.get(ticker, {})
        change_pct = data.get("change_pct")
        if change_pct is not None:
            directions.append({"ticker": ticker, "change_pct": change_pct})

    if len(directions) < 2:
        return None

    # Simple check: are all positions moving the same way by a significant amount?
    all_positive = all(d["change_pct"] > 0.5 for d in directions)
    all_negative = all(d["change_pct"] < -0.5 for d in directions)

    if all_positive or all_negative:
        direction = "up" if all_positive else "down"
        return {
            "type": "correlation",
            "direction": direction,
            "positions": directions,
        }
    return None


def _check_stop_losses(portfolio: dict, instruments: dict) -> list[dict]:
    """Check positions for stop-loss breaches."""
    alerts = []
    for pos in portfolio.get("positions", []):
        ticker = pos["ticker"]
        entry_price = pos["entry_price"]
        data = instruments.get(ticker, {})
        current_price = data.get("price")
        if current_price is None:
            continue
        drop_pct = ((entry_price - current_price) / entry_price) * 100
        if drop_pct >= config.STOP_LOSS_PCT:
            alerts.append({
                "type": "stop_loss",
                "ticker": ticker,
                "entry_price": entry_price,
                "current_price": current_price,
                "drop_pct": round(drop_pct, 2),
                "quantity": pos["quantity"],
            })
    return alerts


def _update_trailing_stops(portfolio: dict, instruments: dict) -> list[dict]:
    """Update trailing stops for all positions and check for breaches.
    Also checks take-profit targets. Returns list of auto-trade actions."""
    auto_trades = []
    from regime import load_regime
    regime_data = load_regime()
    regime_params = regime_data.get("parameters", {})
    trailing_mult = regime_params.get("stop_atr_multiplier", config.TRAILING_STOP_ATR_MULTIPLIER)

    # Fetch ATR data for stop calculations
    try:
        technicals = fetch_technical_indicators()
    except Exception:
        technicals = {}

    for pos in portfolio.get("positions", []):
        ticker = pos["ticker"]
        data = instruments.get(ticker, {})
        current_price = data.get("price")
        if current_price is None:
            continue

        entry_price = pos["entry_price"]
        atr = technicals.get(ticker, {}).get("atr_14")

        # Update highest price since entry
        highest = max(pos.get("highest_since_entry", entry_price), current_price)
        pos["highest_since_entry"] = round(highest, 2)
        pos["current_price"] = current_price
        pos["unrealized_pnl"] = round((current_price - entry_price) * pos["quantity"], 2)

        # Update trailing stop if we have ATR
        if atr and atr > 0:
            new_trailing = round(highest - trailing_mult * atr, 2)
            old_trailing = pos.get("trailing_stop")
            # Trailing stop only moves up, never down
            if old_trailing is None or new_trailing > old_trailing:
                pos["trailing_stop"] = new_trailing

        # Check trailing stop breach
        trailing_stop = pos.get("trailing_stop")
        if trailing_stop is not None and current_price <= trailing_stop:
            auto_trades.append({
                "type": "trailing_stop",
                "action": "SELL",
                "ticker": ticker,
                "quantity": pos["quantity"],
                "price": current_price,
                "reasoning": (
                    f"AUTOMATIC TRAILING STOP: {ticker} at ${current_price} "
                    f"breached trailing stop ${trailing_stop} "
                    f"(highest: ${highest}, ATR mult: {trailing_mult}x)"
                ),
            })
            continue  # Don't check take-profit if we're selling everything

        # Check take-profit targets
        gain_pct = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
        partial_hit = pos.get("take_profit_partial_hit", False)

        if not partial_hit and gain_pct >= config.TAKE_PROFIT_PARTIAL_PCT:
            # Sell 50% at partial take-profit
            sell_qty = round(pos["quantity"] * 0.5, 3)
            if sell_qty > 0:
                pos["take_profit_partial_hit"] = True
                auto_trades.append({
                    "type": "take_profit_partial",
                    "action": "SELL",
                    "ticker": ticker,
                    "quantity": sell_qty,
                    "price": current_price,
                    "reasoning": (
                        f"AUTOMATIC TAKE-PROFIT (50%): {ticker} up {gain_pct:.1f}% "
                        f"from entry ${entry_price} to ${current_price} "
                        f"(threshold: {config.TAKE_PROFIT_PARTIAL_PCT}%)"
                    ),
                })
        elif partial_hit and gain_pct >= config.TAKE_PROFIT_FULL_PCT:
            # Sell remaining at full take-profit
            auto_trades.append({
                "type": "take_profit_full",
                "action": "SELL",
                "ticker": ticker,
                "quantity": pos["quantity"],
                "price": current_price,
                "reasoning": (
                    f"AUTOMATIC TAKE-PROFIT (remaining): {ticker} up {gain_pct:.1f}% "
                    f"from entry ${entry_price} to ${current_price} "
                    f"(threshold: {config.TAKE_PROFIT_FULL_PCT}%)"
                ),
            })

    return auto_trades


def run_risk_monitor() -> dict:
    """Run a risk monitoring cycle. Returns dict of alerts found.

    Now also checks overseas monitor summaries for overnight volatility
    or macro developments that could affect U.S. positions.
    """
    logger.info("Running risk monitor check...")

    portfolio = load_portfolio()
    instruments = fetch_instrument_prices()
    all_alerts = []

    # 0. Check overseas summaries for overnight risk flags
    try:
        from overseas_monitors import get_asia_summary, get_europe_summary, get_handoff_summary
        from exchange_calendar import is_exchange_open, get_schedule_drift_warning

        # Log exchange status
        jpx_open = is_exchange_open("JPX")
        lse_open = is_exchange_open("LSE")
        logger.info(f"Exchange status — JPX: {'open' if jpx_open else 'closed'}, LSE: {'open' if lse_open else 'closed'}")

        drift = get_schedule_drift_warning()
        if drift:
            logger.warning(f"DST drift: {drift}")

        # Prefer handoff summary, fall back to raw feeds
        handoff = get_handoff_summary(1)
        if handoff.strip():
            overseas_context = f"Overnight Handoff: {handoff[:800]}\n"
        else:
            asia = get_asia_summary(1)
            europe = get_europe_summary(1)
            overseas_context = ""
            if asia.strip():
                overseas_context += f"Asia: {asia[:500]}\n"
            if europe.strip():
                overseas_context += f"Europe: {europe[:500]}\n"

        if overseas_context:
            logger.info("Risk monitor ingesting overseas context")
    except Exception as e:
        logger.debug(f"Could not load overseas summaries: {e}")
        overseas_context = ""

    # 1. Update trailing stops and check for auto-trades
    auto_trades = _update_trailing_stops(portfolio, instruments)

    # Execute automatic trades (trailing stops and take-profits)
    auto_executed = []
    if auto_trades:
        # Fetch technicals for stop calculations on new positions
        try:
            technicals = fetch_technical_indicators()
        except Exception:
            technicals = None

        for trade_info in auto_trades:
            trade = {
                "action": trade_info["action"],
                "ticker": trade_info["ticker"],
                "quantity": trade_info["quantity"],
                "price": trade_info["price"],
                "reasoning": trade_info["reasoning"],
            }
            try:
                from agent import validate_trade
                valid, reason = validate_trade(trade, portfolio)
                if valid:
                    logger.warning(f"Auto-executing {trade_info['type']}: {trade['action']} {trade['quantity']}x {trade['ticker']}")
                    portfolio, _ = execute_trade(trade, portfolio, technicals)
                    auto_executed.append(trade_info)
                    all_alerts.append({
                        "type": trade_info["type"],
                        "ticker": trade_info["ticker"],
                        "action": "EXECUTED",
                        "detail": trade_info["reasoning"],
                    })
                else:
                    logger.warning(f"Auto-trade rejected: {reason}")
            except Exception as e:
                logger.error(f"Failed to auto-execute {trade_info['type']} for {trade_info['ticker']}: {e}")
    else:
        # Save updated trailing stops even if no trades
        save_portfolio(portfolio)

    # 2. Stop-loss check (traditional percentage-based)
    sl_alerts = _check_stop_losses(portfolio, instruments)
    all_alerts.extend(sl_alerts)

    # 3. Drawdown check
    dd_alert = _check_drawdown(portfolio)
    if dd_alert:
        all_alerts.append(dd_alert)

    # 4. Volatility check
    vol_alerts = _check_volatility(instruments)
    all_alerts.extend(vol_alerts)

    # 5. Correlation/concentration check
    corr_alert = _check_correlation(portfolio, instruments)
    if corr_alert:
        all_alerts.append(corr_alert)

    if not all_alerts:
        logger.info("Risk monitor: no alerts detected.")
        return {"alerts": [], "action_taken": False, "auto_trades": []}

    # Format alerts
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    descriptions = []

    for a in all_alerts:
        if a["type"] == "stop_loss":
            descriptions.append(
                f"🛑 STOP-LOSS: {a['ticker']} dropped {a['drop_pct']}% "
                f"from entry ${a['entry_price']} → ${a['current_price']} "
                f"({a['quantity']} shares)"
            )
        elif a["type"] == "trailing_stop":
            descriptions.append(f"🔻 TRAILING STOP EXECUTED: {a.get('detail', a['ticker'])}")
        elif a["type"] in ("take_profit_partial", "take_profit_full"):
            descriptions.append(f"💰 TAKE-PROFIT EXECUTED: {a.get('detail', a['ticker'])}")
        elif a["type"] == "drawdown":
            descriptions.append(
                f"📉 DRAWDOWN: Portfolio at ${a['current']:.2f}, "
                f"down {a['drawdown_pct']}% from ATH ${a['ath']:.2f}"
            )
        elif a["type"] == "volatility":
            descriptions.append(
                f"⚡ VOLATILITY: {a['ticker']} intraday range {a['range_pct']}% "
                f"(H: ${a['high']:.2f} L: ${a['low']:.2f})"
            )
        elif a["type"] == "correlation":
            tickers = ", ".join(d["ticker"] for d in a["positions"])
            descriptions.append(
                f"🔗 CORRELATION: All positions ({tickers}) moving {a['direction']} together"
            )

    alert_text = "\n".join(descriptions)
    logger.warning(f"Risk monitor detected {len(all_alerts)} alert(s):\n{alert_text}")

    # Write to risk alerts log
    try:
        with open(config.RISK_ALERTS_PATH, "r"):
            pass
    except FileNotFoundError:
        with open(config.RISK_ALERTS_PATH, "w") as f:
            f.write("# Risk Alerts\n\nAlerts from the risk monitoring agent.\n\n---\n")

    entry = f"""
## Risk Alert - {timestamp}

{alert_text}

---
"""
    append_to_file(config.RISK_ALERTS_PATH, entry)

    # Determine if we need to wake the trader (only for non-auto-handled alerts)
    critical_types = {"stop_loss", "drawdown"}
    has_critical = any(a["type"] in critical_types for a in all_alerts)

    if has_critical:
        logger.warning("Critical risk alert detected — invoking trader for immediate review.")
        try:
            run_hourly_check()
        except Exception as e:
            logger.error(f"Failed to invoke trader from risk monitor: {e}")

    return {
        "alerts": all_alerts,
        "action_taken": has_critical or len(auto_executed) > 0,
        "auto_trades": [t["reasoning"] for t in auto_executed],
        "timestamp": timestamp,
    }
