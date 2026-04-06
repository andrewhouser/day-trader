"""Speculation agent: identifies asymmetric opportunities with measured risk.

Counterbalances the system's conservative bias by actively looking for
setups where the potential upside significantly outweighs the downside.
Produces speculative theses that the trading agent evaluates alongside
its normal scoring framework — it suggests, it doesn't execute.

Runs 3x daily during market hours (10 AM, 1 PM, 3 PM ET).
"""
import json
import logging
from datetime import datetime

import config
from agent import call_ollama, load_portfolio, read_recent_entries
from market_data import fetch_technical_indicators, get_technicals_summary

logger = logging.getLogger(__name__)

SPECULATION_SYSTEM = (
    "You are a speculative opportunity analyst for a paper trading portfolio. "
    "Your job is to find asymmetric risk/reward setups that a conservative trading "
    "agent might overlook. You are NOT reckless — you look for situations where "
    "the technical setup, catalyst, or market structure creates a favorable skew "
    "(potential gain significantly exceeds potential loss). You always define a "
    "clear invalidation point and suggest reduced position sizes. "
    "Be specific with numbers, levels, and timeframes."
)


def _get_speculation_model() -> str:
    return config.SPECULATION_MODEL or config.RESEARCH_MODEL


def run_speculation() -> str:
    """Run the speculation analysis cycle.

    Scans all instruments for setups where risk/reward is asymmetrically
    favorable, then writes structured speculative theses to speculation.md.
    """
    logger.info("Starting speculation analysis...")

    portfolio = load_portfolio()
    technicals = fetch_technical_indicators()
    technicals_summary = get_technicals_summary()

    # Read context the speculation agent needs
    recent_research = read_recent_entries(config.RESEARCH_PATH, 3)
    recent_sentiment = read_recent_entries(config.SENTIMENT_PATH, 2)
    recent_trades = read_recent_entries(config.TRADE_LOG_PATH, 5)

    held_tickers = [p["ticker"] for p in portfolio.get("positions", [])]
    cash_pct = (portfolio["cash_usd"] / portfolio["total_value_usd"] * 100) if portfolio["total_value_usd"] > 0 else 100

    # Build instrument snapshot for the prompt
    instrument_snapshots = []
    for ticker, info in config.INSTRUMENTS.items():
        t = technicals.get(ticker, {})
        if not t:
            continue
        snapshot = {
            "ticker": ticker,
            "type": info["tracks"],
            "price": t.get("price"),
            "sma_20": t.get("sma_20"),
            "sma_50": t.get("sma_50"),
            "rsi": t.get("rsi_14"),
            "macd_hist": t.get("macd_histogram"),
            "atr": t.get("atr_14"),
            "bb_upper": t.get("bb_upper"),
            "bb_lower": t.get("bb_lower"),
            "roc_20": t.get("roc_20"),
            "obv_trend": t.get("obv_trend"),
            "held": ticker in held_tickers,
        }
        instrument_snapshots.append(snapshot)

    prompt = f"""Speculation Analysis — {datetime.now().strftime('%Y-%m-%d %H:%M ET')}

You are scanning for asymmetric opportunities the conservative trading agent might miss.
The portfolio is {cash_pct:.0f}% cash with ${portfolio['cash_usd']:.2f} available.

### Instrument Technicals
```json
{json.dumps(instrument_snapshots, indent=2, default=str)}
```

### Recent Research
{recent_research[:2000] if recent_research else "No research available."}

### Recent Sentiment
{recent_sentiment[:1000] if recent_sentiment else "No sentiment data."}

### Recent Trades
{recent_trades[:1000] if recent_trades else "No recent trades."}

---

Identify 1-3 speculative opportunities. For each, you MUST provide ALL of these fields
in a JSON block:

```json
{{
  "speculations": [
    {{
      "ticker": "XYZ",
      "setup": "One sentence describing the technical/fundamental setup",
      "catalyst": "What specific event or condition could trigger the move",
      "direction": "bullish" or "bearish",
      "target_pct": 3.5,
      "stop_pct": 1.5,
      "reward_risk_ratio": 2.3,
      "confidence": "High" or "Medium" or "Low",
      "timeframe": "1-3 sessions",
      "suggested_size_pct": 5.0,
      "invalidation": "Specific price level or condition that kills the thesis"
    }}
  ]
}}
```

RULES:
- reward_risk_ratio MUST be >= 1.5 (asymmetric or don't bother)
- suggested_size_pct should be 3-8% of portfolio (this is speculation, not conviction)
- You MUST have a concrete invalidation point — no vague "if the market drops"
- Prefer setups where: RSI is at extremes (oversold bounce or overbought short), price is
  near Bollinger Band edges, there's a catalyst within 1-3 sessions, or OBV diverges from price
- Contrarian setups are welcome IF you can articulate why the crowd is wrong
- Do NOT suggest instruments already held unless you're suggesting adding to a winner
- If you genuinely see no asymmetric setups, return an empty speculations array and explain why

After the JSON block, write a 2-3 sentence "Speculation Narrative" summarizing the overall
opportunity landscape and what you're watching for."""

    response = call_ollama(
        prompt,
        system=SPECULATION_SYSTEM,
        model=_get_speculation_model(),
        timeout=config.SPECULATION_TIMEOUT,
    )

    if response.startswith("[ERROR]"):
        logger.error(f"Speculation agent LLM failed: {response}")
        return response

    # Parse speculations from response
    speculations = _parse_speculations(response)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"""
## Speculation Analysis — {timestamp}
**Opportunities found:** {len(speculations)}

{response}

---
"""
    from agent import append_to_file
    append_to_file(config.SPECULATION_PATH, entry)
    logger.info(f"Speculation analysis saved ({len(speculations)} opportunities, {len(response)} chars)")
    return response


def _parse_speculations(response: str) -> list[dict]:
    """Extract structured speculation entries from the LLM response."""
    import re
    speculations = []
    json_pattern = r'```json\s*(.*?)\s*```'
    for match in re.findall(json_pattern, response, re.DOTALL):
        try:
            data = json.loads(match)
            if isinstance(data, dict) and "speculations" in data:
                for spec in data["speculations"]:
                    if spec.get("ticker") and spec.get("setup"):
                        speculations.append(spec)
        except (json.JSONDecodeError, TypeError):
            continue
    return speculations


def get_speculation_for_prompt(max_entries: int = 2) -> str:
    """Read the latest speculation entries for injection into the trading prompt."""
    raw = read_recent_entries(config.SPECULATION_PATH, max_entries)
    if not raw.strip():
        return ""
    return raw
