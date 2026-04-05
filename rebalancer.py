"""Portfolio rebalancer agent: runs weekly to analyze overall allocation,
sector exposure, and cash drag. Suggests or executes rebalancing trades."""
import json
import logging
from datetime import datetime

import config
from agent import (
    append_to_file,
    call_ollama,
    execute_trade,
    load_portfolio,
    read_recent_entries,
    validate_trade,
)
from market_data import fetch_instrument_prices

logger = logging.getLogger(__name__)

REBALANCER_SYSTEM = (
    "You are a portfolio rebalancing analyst. You evaluate portfolio allocation, "
    "concentration risk, and cash efficiency. You suggest specific rebalancing "
    "trades with exact quantities and prices. Be conservative — only suggest "
    "trades when drift is meaningful. Output trades as JSON blocks."
)


def _analyze_allocation(portfolio: dict, instruments: dict) -> dict:
    """Compute current allocation percentages and drift from targets."""
    total = portfolio["total_value_usd"]
    if total <= 0:
        return {"cash_pct": 100, "positions": {}, "total": 0}

    cash_pct = (portfolio["cash_usd"] / total) * 100
    position_allocations = {}

    for pos in portfolio["positions"]:
        ticker = pos["ticker"]
        current_price = instruments.get(ticker, {}).get("price", pos["current_price"])
        value = pos["quantity"] * current_price
        pct = (value / total) * 100
        position_allocations[ticker] = {
            "value": round(value, 2),
            "pct": round(pct, 2),
            "quantity": pos["quantity"],
            "entry_price": pos["entry_price"],
            "current_price": current_price,
            "unrealized_pnl": round((current_price - pos["entry_price"]) * pos["quantity"], 2),
        }

    return {
        "cash_pct": round(cash_pct, 2),
        "positions": position_allocations,
        "total": total,
    }


def run_rebalancer() -> str:
    """Run the weekly portfolio rebalancing analysis."""
    logger.info("Starting weekly portfolio rebalance analysis...")

    portfolio = load_portfolio()
    instruments = fetch_instrument_prices()
    allocation = _analyze_allocation(portfolio, instruments)
    recent_research = read_recent_entries(config.RESEARCH_PATH, 3)
    recent_reflections = read_recent_entries(config.REFLECTIONS_PATH, 5)

    # Read lessons if available
    try:
        with open(config.LESSONS_PATH, "r") as f:
            lessons = f.read()[-2000:]  # last 2000 chars
    except FileNotFoundError:
        lessons = "No lessons file yet."

    prompt = f"""Weekly Portfolio Rebalance Review

### Current Portfolio
```json
{json.dumps(portfolio, indent=2)}
```

### Current Allocation
- Cash: {allocation['cash_pct']}% (target: {config.REBALANCER_TARGET_CASH_PCT}%)
- Positions:
{json.dumps(allocation['positions'], indent=2) if allocation['positions'] else "  None — fully in cash"}

### Allocation Rules
- Target cash allocation: {config.REBALANCER_TARGET_CASH_PCT}%
- Max single position: {config.MAX_POSITION_PCT * 100}%
- Drift threshold for rebalance: {config.REBALANCER_DRIFT_THRESHOLD}%
- Allowed instruments: {', '.join(config.INSTRUMENTS.keys())}

### Recent Research
{recent_research}

### Trading Lessons
{lessons}

### Recent Reflections
{recent_reflections}

---

Analyze the portfolio and determine if rebalancing is needed. Consider:

1. **Cash Allocation:** Is cash too high (drag on returns) or too low (insufficient dry powder)?
2. **Position Concentration:** Is any single position too large relative to the 25% max?
3. **Sector/Geography Exposure:** Are we overweight U.S. vs international? Any blind spots?
4. **Winners & Losers:** Should we trim winners that have grown beyond target allocation?
   Should we cut losers that aren't recovering?
5. **Opportunity Cost:** Given current market conditions from research, would capital be
   better deployed elsewhere?

If rebalancing is needed, output specific trades as JSON blocks:
```json
{{
  "action": "BUY" or "SELL",
  "ticker": "SPY",
  "quantity": 1,
  "price": <current_price>,
  "reasoning": "Rebalancing: <specific reason>"
}}
```

If no rebalancing is needed, explain why the current allocation is acceptable.
End with a brief allocation summary table."""

    logger.info("Sending rebalance prompt to LLM...")
    response = call_ollama(prompt, system=REBALANCER_SYSTEM, model=config.RESEARCH_MODEL)
    logger.info(f"Rebalancer response received ({len(response)} chars)")

    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    # Parse and execute any rebalancing trades
    from agent import parse_trades_from_response
    trades = parse_trades_from_response(response, portfolio)
    executed = []

    if trades:
        for trade in trades:
            valid, reason = validate_trade(trade, portfolio)
            if valid:
                logger.info(f"Rebalancer executing: {trade['action']} {trade['quantity']}x {trade['ticker']}")
                portfolio, _ = execute_trade(trade, portfolio, None)
                executed.append(trade)
            else:
                logger.warning(f"Rebalancer trade rejected: {reason}")

    # Log the rebalance analysis
    report_path = f"{config.REPORTS_DIR}/{now.strftime('%Y-%m-%d')}_rebalance.md"
    with open(report_path, "w") as f:
        f.write(f"# Rebalance Report - {now.strftime('%Y-%m-%d')}\n\n")
        f.write(f"Trades executed: {len(executed)}\n\n")
        f.write(response)

    logger.info(f"Rebalance report saved to {report_path}")
    logger.info(f"Rebalancer complete: {len(executed)} trades executed")

    return response
