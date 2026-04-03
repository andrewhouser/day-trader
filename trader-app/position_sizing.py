"""Volatility-scaled position sizing module.

Calculates position sizes based on ATR and portfolio risk budget,
adjusted by the current market regime multiplier."""
import logging

import config

logger = logging.getLogger(__name__)


def calculate_position_size(
    ticker: str,
    price: float,
    atr: float | None,
    portfolio_value: float,
    regime_params: dict | None = None,
) -> dict:
    """Calculate the recommended position size for an instrument.

    Uses: (risk_budget / ATR) to determine share count, then caps at
    the regime-adjusted max position percentage.

    Args:
        ticker: Instrument ticker symbol.
        price: Current price per share.
        atr: 14-period Average True Range. If None, uses a conservative default.
        portfolio_value: Total portfolio value in USD.
        regime_params: Regime-specific parameters (from config.REGIME_PARAMS).

    Returns:
        Dict with recommended quantity, dollar amount, and reasoning.
    """
    if regime_params is None:
        regime_params = config.REGIME_PARAMS.get("SIDEWAYS", {})

    risk_budget_pct = config.RISK_BUDGET_PCT / 100.0
    risk_budget_usd = portfolio_value * risk_budget_pct
    regime_multiplier = regime_params.get("regime_multiplier", 1.0)
    max_pct = regime_params.get("max_position_pct", config.MAX_POSITION_PCT)

    # Apply regime multiplier to risk budget
    adjusted_risk = risk_budget_usd * regime_multiplier

    # If no ATR, use 2% of price as conservative estimate
    effective_atr = atr if atr and atr > 0 else price * 0.02

    # Shares = risk_budget / ATR (how many shares can we lose 1 ATR on)
    shares_from_risk = adjusted_risk / effective_atr if effective_atr > 0 else 0

    # Dollar value of that position
    dollar_value = shares_from_risk * price

    # Cap at max position size
    max_dollar = portfolio_value * max_pct
    # Also cap at absolute ceiling of 25%
    absolute_max = portfolio_value * config.MAX_POSITION_PCT

    if dollar_value > min(max_dollar, absolute_max):
        dollar_value = min(max_dollar, absolute_max)
        shares_from_risk = dollar_value / price if price > 0 else 0

    # Round to reasonable precision
    quantity = round(shares_from_risk, 3)
    dollar_value = round(dollar_value, 2)
    pct_of_portfolio = round((dollar_value / portfolio_value) * 100, 1) if portfolio_value > 0 else 0

    return {
        "ticker": ticker,
        "recommended_quantity": quantity,
        "recommended_dollar_value": dollar_value,
        "pct_of_portfolio": pct_of_portfolio,
        "atr_used": round(effective_atr, 4),
        "risk_budget_usd": round(adjusted_risk, 2),
        "regime_multiplier": regime_multiplier,
        "max_position_pct": max_pct * 100,
    }


def get_all_position_sizes(
    technicals: dict,
    portfolio_value: float,
    regime_params: dict | None = None,
) -> dict:
    """Calculate position sizes for all instruments.

    Args:
        technicals: Dict of technical indicators per ticker.
        portfolio_value: Total portfolio value.
        regime_params: Current regime parameters.

    Returns:
        Dict keyed by ticker with position sizing recommendations.
    """
    results = {}
    for ticker in config.INSTRUMENTS:
        data = technicals.get(ticker, {})
        price = data.get("price")
        atr = data.get("atr_14")
        if price is None:
            continue
        results[ticker] = calculate_position_size(
            ticker=ticker,
            price=price,
            atr=atr,
            portfolio_value=portfolio_value,
            regime_params=regime_params,
        )
    return results


def get_sizing_summary(technicals: dict, portfolio_value: float, regime_params: dict | None = None) -> str:
    """Build a text summary of position sizing for the LLM prompt."""
    sizes = get_all_position_sizes(technicals, portfolio_value, regime_params)
    if not sizes:
        return "\n### Position Sizing\nNo sizing data available.\n"

    lines = ["\n### Recommended Position Sizes (volatility-scaled)\n"]
    for ticker, s in sorted(sizes.items()):
        lines.append(
            f"- {ticker}: {s['recommended_quantity']} shares "
            f"(${s['recommended_dollar_value']}, {s['pct_of_portfolio']}% of portfolio) "
            f"| ATR: {s['atr_used']} | Risk budget: ${s['risk_budget_usd']}"
        )
    return "\n".join(lines)
