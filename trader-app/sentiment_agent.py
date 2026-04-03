"""Sentiment agent: scrapes financial news via yfinance and scores
sentiment per instrument using the LLM. Writes sentiment.md for the
trader to consume alongside research notes."""
import json
import logging
from datetime import datetime

import yfinance as yf

import config
from agent import append_to_file, call_ollama

logger = logging.getLogger(__name__)

SENTIMENT_SYSTEM = (
    "You are a financial sentiment analyst. You read news headlines and "
    "produce concise, structured sentiment scores. Be objective and data-driven. "
    "Do not speculate beyond what the headlines support."
)


def _fetch_news() -> dict[str, list[str]]:
    """Fetch recent news headlines for each instrument via yfinance."""
    all_news: dict[str, list[str]] = {}
    tickers = list(config.INSTRUMENTS.keys()) + list(config.INDICES.keys())

    for symbol in tickers:
        try:
            ticker = yf.Ticker(symbol)
            news = ticker.news or []
            headlines = [item.get("title", "") for item in news[:8] if item.get("title")]
            if headlines:
                label = config.INSTRUMENTS.get(symbol, {}).get("tracks") or config.INDICES.get(symbol, symbol)
                all_news[f"{symbol} ({label})"] = headlines
        except Exception as e:
            logger.warning(f"Failed to fetch news for {symbol}: {e}")

    return all_news


def run_sentiment() -> str:
    """Run a sentiment analysis cycle."""
    logger.info("Starting sentiment analysis cycle...")

    news = _fetch_news()
    if not news:
        logger.warning("No news headlines fetched, skipping sentiment cycle.")
        return ""

    # Build a compact news summary for the LLM
    news_block = ""
    for symbol, headlines in news.items():
        news_block += f"\n### {symbol}\n"
        for h in headlines:
            news_block += f"- {h}\n"

    prompt = f"""Sentiment Analysis Task

Analyze the following recent news headlines for financial instruments and indices.
For each instrument/index that has news, provide:

1. **Sentiment Score:** -2 (very bearish) to +2 (very bullish), with 0 being neutral
2. **Confidence:** Low / Medium / High
3. **Key Theme:** One sentence summarizing the dominant narrative
4. **Trading Implication:** One sentence on what this means for trading decisions

{news_block}

---

After scoring each instrument, provide:

### Overall Market Sentiment
- A 1-2 sentence summary of the aggregate sentiment across all instruments
- Whether sentiment is diverging between U.S. and international markets
- Any headline risks that could cause sudden moves

Format each instrument score as:
**TICKER** | Score: X | Confidence: Y | Theme: ... | Implication: ..."""

    logger.info("Sending sentiment prompt to LLM...")
    response = call_ollama(prompt, system=SENTIMENT_SYSTEM, model=config.SENTIMENT_MODEL)
    logger.info(f"Sentiment response received ({len(response)} chars)")

    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    entry = f"""
## Sentiment Analysis - {timestamp}

{response}

---
"""
    # Ensure file exists
    try:
        with open(config.SENTIMENT_PATH, "r") as f:
            pass
    except FileNotFoundError:
        with open(config.SENTIMENT_PATH, "w") as f:
            f.write("# Sentiment Log\n\nSentiment scores from news headline analysis.\n\n---\n")

    append_to_file(config.SENTIMENT_PATH, entry)
    logger.info(f"Sentiment analysis saved to {config.SENTIMENT_PATH}")

    return response
