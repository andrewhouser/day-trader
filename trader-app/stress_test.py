"""Portfolio stress test — runs hypothetical shock scenarios against
the current portfolio to estimate downside risk."""
import logging

import config

logger = logging.getLogger(__name__)

# Approximate betas for correlated moves in SPY drop scenario
BETA_MAP = {
    "SPY": 1.0, "QQQ": 1.0, "DIA": 1.0,
    "XLK": 1.2, "XLF": 1.2, "XLE": 1.2, "XLI": 1.2, "XBI": 1.2,
    "XLV": 0.8, "XLP": 0.6, "XLU": 0.6,
    "EWJ": 0.8, "EWU": 0.8, "EWG": 0.8,
    "TLT": 0.3, "SHY": 0.1, "AGG": 0.3,
    "GLD": -0.2, "SLV": -0.2,
    "USO": 0.0,
}

# Sector rotation scenario: tech drops, defensives rise
SECTOR_ROTATION_SHOCKS = {
    "XLK": -0.08, "QQQ": -0.08,
    "XLF": -0.04, "XLI": -0.03,
    "TLT": 0.02, "GLD": 0.01, "XLU": 0.01,
}


def _check_stop_breach(pos: dict, shocked_price: float) -> dict | None:
    """Check if a shocked price breaches trailing or initial stop."""
    trailing = pos.get("trailing_stop")
    initial = pos.get("initial_stop")
    if trailing is not None and shocked_price <= trailing:
        loss = round((pos["entry_price"] - shocked_price) * pos["quantity"], 2)
        return {"ticker": pos["ticker"], "stop_type": "trailing_stop", "estimated_loss": loss}
    if initial is not None and shocked_price <= initial:
        loss = round((pos["entry_price"] - shocked_price) * pos["quantity"], 2)
        return {"ticker": pos["ticker"], "stop_type": "initial_stop", "estimated_loss": loss}
    return None


def _scenario_spy_drop(portfolio: dict, instruments: dict) -> dict:
    """Scenario A: SPY drops 5%, correlated moves across all positions."""
    drop = 0.05
    positions = portfolio.get("positions", [])
    cash = portfolio["cash_usd"]
    stopped_out = []
    shocked_value = cash

    for pos in positions:
        ticker = pos["ticker"]
        current = instruments.get(ticker, {}).get("price", pos["current_price"])
        beta = BETA_MAP.get(ticker, 0.5)
        shocked_price = round(current * (1 - drop * beta), 2)

        breach = _check_stop_breach(pos, shocked_price)
        if breach:
            stopped_out.append(breach)

        shocked_value += pos["quantity"] * shocked_price

    shocked_value = round(shocked_value, 2)
    current_value = portfolio["total_value_usd"]
    pct_change = round(((shocked_value - current_value) / current_value) * 100, 2) if current_value else 0

    stopped_tickers = [s["ticker"] for s in stopped_out]
    summary = (
        f"A 5% SPY drop would reduce the portfolio from ${current_value:.2f} to ${shocked_value:.2f} "
        f"({pct_change:+.2f}%). "
    )
    if stopped_out:
        summary += f"{len(stopped_out)} position(s) would hit stops: {', '.join(stopped_tickers)}."
    else:
        summary += "No positions would hit stop-loss levels."

    return {
        "name": "SPY -5% Shock",
        "description": "SPY drops 5% with correlated moves across all holdings based on approximate beta.",
        "shocked_value": shocked_value,
        "pct_change": pct_change,
        "positions_stopped_out": stopped_out,
        "summary": summary,
    }


def _scenario_vix_spike(portfolio: dict, instruments: dict) -> dict:
    """Scenario B: VIX spikes to 30, triggering high-volatility regime limits."""
    positions = portfolio.get("positions", [])
    total_value = portfolio["total_value_usd"]
    max_pct = 0.10  # HIGH_VOLATILITY regime cap

    oversized = []
    forced_reduction = 0.0

    for pos in positions:
        ticker = pos["ticker"]
        current = instruments.get(ticker, {}).get("price", pos["current_price"])
        pos_value = pos["quantity"] * current
        pos_pct = round((pos_value / total_value) * 100, 2) if total_value else 0

        if pos_pct > max_pct * 100:
            excess_value = pos_value - (total_value * max_pct)
            oversized.append({"ticker": ticker, "current_pct": pos_pct})
            forced_reduction += excess_value

    forced_reduction = round(forced_reduction, 2)
    summary = f"A VIX spike to 30 would trigger high-volatility regime (max 10% per position). "
    if oversized:
        tickers = [o["ticker"] for o in oversized]
        summary += (
            f"{len(oversized)} position(s) oversized: {', '.join(tickers)}. "
            f"Estimated ${forced_reduction:.2f} in forced reductions needed."
        )
    else:
        summary += "All positions are within the 10% limit — no forced reductions needed."

    return {
        "name": "VIX Spike to 30",
        "description": "VIX spikes to 30, triggering high-volatility regime with 10% max position size.",
        "shocked_value": total_value,
        "pct_change": 0.0,
        "positions_stopped_out": [],
        "positions_oversized": oversized,
        "forced_reduction_cost": forced_reduction,
        "summary": summary,
    }


def _scenario_sector_rotation(portfolio: dict, instruments: dict) -> dict:
    """Scenario C: Tech drops 8% over 3 sessions, defensives rise."""
    positions = portfolio.get("positions", [])
    cash = portfolio["cash_usd"]
    stopped_out = []
    shocked_value = cash

    for pos in positions:
        ticker = pos["ticker"]
        current = instruments.get(ticker, {}).get("price", pos["current_price"])
        shock = SECTOR_ROTATION_SHOCKS.get(ticker, 0.0)
        shocked_price = round(current * (1 + shock), 2)

        breach = _check_stop_breach(pos, shocked_price)
        if breach:
            stopped_out.append(breach)

        shocked_value += pos["quantity"] * shocked_price

    shocked_value = round(shocked_value, 2)
    current_value = portfolio["total_value_usd"]
    pct_change = round(((shocked_value - current_value) / current_value) * 100, 2) if current_value else 0

    stopped_tickers = [s["ticker"] for s in stopped_out]
    summary = (
        f"A tech sector rotation (XLK/QQQ -8%) would move the portfolio from "
        f"${current_value:.2f} to ${shocked_value:.2f} ({pct_change:+.2f}%). "
    )
    if stopped_out:
        summary += f"{len(stopped_out)} position(s) would hit stops: {', '.join(stopped_tickers)}."
    else:
        summary += "No positions would hit stop-loss levels."

    return {
        "name": "Tech Sector Rotation",
        "description": "XLK and QQQ drop 8% over 3 sessions. Financials and industrials drop 3-4%. Defensives rise 1-2%.",
        "shocked_value": shocked_value,
        "pct_change": pct_change,
        "positions_stopped_out": stopped_out,
        "summary": summary,
    }


def run_stress_test(portfolio: dict, instruments: dict, technicals: dict) -> dict:
    """Run three standard scenarios against the current portfolio."""
    scenarios = [
        _scenario_spy_drop(portfolio, instruments),
        _scenario_vix_spike(portfolio, instruments),
        _scenario_sector_rotation(portfolio, instruments),
    ]

    return {
        "scenarios": scenarios,
        "current_portfolio_value": portfolio["total_value_usd"],
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }
