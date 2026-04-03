"""Events calendar agent: fetches upcoming economic events and earnings
dates, writes events.md so the trader can factor in scheduled catalysts."""
import json
import logging
from datetime import datetime, timedelta

import yfinance as yf

import config
from agent import call_ollama

logger = logging.getLogger(__name__)

EVENTS_SYSTEM = (
    "You are a financial calendar analyst. You identify upcoming economic events, "
    "earnings dates, and scheduled catalysts that could move markets. Be specific "
    "with dates and expected impact. Focus on events relevant to ETF trading."
)


def _fetch_earnings_calendar() -> list[dict]:
    """Fetch upcoming earnings/events for tracked instruments via yfinance."""
    events = []

    for ticker_sym, info in config.INSTRUMENTS.items():
        try:
            ticker = yf.Ticker(ticker_sym)
            cal = ticker.calendar
            if cal is not None and not (hasattr(cal, "empty") and cal.empty):
                if isinstance(cal, dict):
                    for key, value in cal.items():
                        events.append({
                            "ticker": ticker_sym,
                            "event": str(key),
                            "detail": str(value),
                        })
        except Exception as e:
            logger.debug(f"No calendar data for {ticker_sym}: {e}")

    return events


def _fetch_major_holdings_events() -> list[dict]:
    """Check major ETF holdings for upcoming earnings."""
    events = []
    # Check top holdings of SPY and QQQ for earnings
    for etf_sym in ["SPY", "QQQ"]:
        try:
            etf = yf.Ticker(etf_sym)
            # yfinance may not always have this, so we handle gracefully
            info = etf.info or {}
            events.append({
                "ticker": etf_sym,
                "event": "ETF Info",
                "detail": f"52w range: {info.get('fiftyTwoWeekLow', 'N/A')}-{info.get('fiftyTwoWeekHigh', 'N/A')}",
            })
        except Exception as e:
            logger.debug(f"No holdings events for {etf_sym}: {e}")

    return events


def run_events_calendar() -> str:
    """Run the daily events calendar update."""
    logger.info("Starting events calendar update...")

    instrument_events = _fetch_earnings_calendar()
    holdings_events = _fetch_major_holdings_events()
    all_events = instrument_events + holdings_events

    today = datetime.now()
    week_ahead = today + timedelta(days=7)

    events_block = ""
    if all_events:
        events_block = "### Data from yfinance\n"
        for e in all_events:
            events_block += f"- {e['ticker']}: {e['event']} — {e['detail']}\n"
    else:
        events_block = "No specific calendar events found via yfinance.\n"

    prompt = f"""Daily Economic Events Calendar

Today is {today.strftime('%A, %B %d, %Y')}.
Generate an events calendar for the next 7 days ({today.strftime('%Y-%m-%d')} to {week_ahead.strftime('%Y-%m-%d')}).

{events_block}

Based on your knowledge of the typical economic calendar, list:

1. **Scheduled Economic Data Releases**
   - Federal Reserve meetings/minutes (FOMC)
   - Jobs reports (NFP, unemployment claims)
   - CPI/PPI inflation data
   - GDP releases
   - PMI/ISM manufacturing/services
   - Consumer confidence/sentiment
   - Retail sales
   - Any other major releases this week

2. **Market Events**
   - Options expiration dates
   - Index rebalancing dates
   - Notable earnings from major companies that could move ETFs

3. **International Events**
   - Bank of Japan, Bank of England, ECB decisions
   - Major international economic data
   - Events affecting EWJ, EWU, EWG specifically

For each event, provide:
- **Date** (or expected date)
- **Event name**
- **Expected impact:** High / Medium / Low
- **Trading implication:** One sentence on how this could affect our instruments

End with a **Trading Calendar Summary**: which days this week are highest risk
for holding positions, and whether to reduce exposure ahead of any events.

Note: Use your best knowledge of the typical economic calendar schedule.
If you're unsure of exact dates, note that and provide the typical schedule."""

    logger.info("Sending events prompt to LLM...")
    response = call_ollama(prompt, system=EVENTS_SYSTEM, model=config.RESEARCH_MODEL)
    logger.info(f"Events calendar received ({len(response)} chars)")

    timestamp = today.strftime("%Y-%m-%d %H:%M:%S")

    # Write events.md (overwrite — this is a rolling calendar, not a log)
    with open(config.EVENTS_PATH, "w") as f:
        f.write(f"# Economic Events Calendar\n\n")
        f.write(f"Last updated: {timestamp}\n\n")
        f.write(response)

    # Also save a dated snapshot
    report_path = f"{config.REPORTS_DIR}/{today.strftime('%Y-%m-%d')}_events.md"
    with open(report_path, "w") as f:
        f.write(f"# Events Calendar - {today.strftime('%Y-%m-%d')}\n\n")
        f.write(response)

    logger.info(f"Events calendar saved to {config.EVENTS_PATH}")
    return response
