"""Sentiment agent: gathers financial news from multiple sources and scores
sentiment per instrument using the LLM. Writes sentiment.md for the
trader to consume alongside research notes.

News source priority:
  1. Finnhub (general + company news) — requires FINNHUB_API_KEY
  2. Finviz RSS feed — no key required, public RSS
  3. yfinance ticker.news — fallback if both above fail
"""
import json
import logging
import os
import re
from datetime import datetime

import requests

import config
from agents.agent import append_to_file, call_ollama

logger = logging.getLogger(__name__)

SENTIMENT_SYSTEM = (
    "You are a financial sentiment analyst. You read news headlines and "
    "produce concise, structured sentiment scores. Be objective and data-driven. "
    "Do not speculate beyond what the headlines support."
)

FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "")
FINNHUB_BASE = "https://finnhub.io/api/v1"
FINVIZ_RSS = "https://finviz.com/news_export.ashx?v=3"

# RSS feeds that work without API keys from Docker containers
_RSS_FEEDS = {
    "Google Finance (Market)": "https://news.google.com/rss/search?q=stock+market+today&hl=en-US&gl=US&ceid=US:en",
    "Google Finance (Economy)": "https://news.google.com/rss/search?q=economy+federal+reserve&hl=en-US&gl=US&ceid=US:en",
    "CNBC Markets": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
    "CNBC Economy": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910266",
}


def _fetch_finnhub_news() -> dict[str, list[str]]:
    """Fetch news from Finnhub: general market news + company news for key instruments."""
    if not FINNHUB_KEY:
        logger.info("[sentiment] No FINNHUB_API_KEY — skipping Finnhub source")
        return {}

    all_news: dict[str, list[str]] = {}
    session = requests.Session()

    # General market news
    try:
        resp = session.get(
            f"{FINNHUB_BASE}/news",
            params={"category": "general", "token": FINNHUB_KEY},
            timeout=15,
        )
        if resp.status_code == 429:
            logger.warning("[sentiment/finnhub] rate limited on general news")
        elif resp.ok:
            items = resp.json()[:20]
            general = [item.get("headline", "") for item in items if item.get("headline")]
            if general:
                all_news["Market News (General)"] = general
                logger.info(f"[sentiment/finnhub] {len(general)} general headlines")
    except Exception as e:
        logger.error(f"[sentiment/finnhub] general news error: {e}")

    # Company news for top instruments
    today = datetime.utcnow().strftime("%Y-%m-%d")
    symbols = list(config.INSTRUMENTS.keys())[:10]
    for sym in symbols:
        try:
            resp = session.get(
                f"{FINNHUB_BASE}/company-news",
                params={"symbol": sym, "from": today, "to": today, "token": FINNHUB_KEY},
                timeout=15,
            )
            if resp.status_code == 429:
                logger.warning(f"[sentiment/finnhub] rate limited on {sym}")
                break
            if resp.ok:
                items = resp.json()[:5]
                headlines = [item.get("headline", "") for item in items if item.get("headline")]
                if headlines:
                    label = config.INSTRUMENTS.get(sym, {}).get("tracks", sym)
                    all_news[f"{sym} ({label})"] = headlines
        except Exception as e:
            logger.warning(f"[sentiment/finnhub] company news error for {sym}: {e}")

    return all_news


def _fetch_finviz_news() -> dict[str, list[str]]:
    """Fetch market news headlines from Finviz RSS feed (no API key needed)."""
    try:
        import xml.etree.ElementTree as ET

        resp = requests.get(
            FINVIZ_RSS,
            headers={"User-Agent": "TraderResearchAgent/1.0"},
            timeout=15,
        )
        if resp.status_code in (403, 429):
            logger.warning(f"[sentiment/finviz] HTTP {resp.status_code}")
            return {}
        resp.raise_for_status()

        root = ET.fromstring(resp.text)
        headlines = []
        for item in root.findall(".//item"):
            title = item.findtext("title", "").strip()
            if title:
                headlines.append(title)

        if not headlines:
            return {}

        logger.info(f"[sentiment/finviz] {len(headlines)} headlines from RSS")

        # Group by detected instrument symbols
        grouped: dict[str, list[str]] = {"Market News (Finviz)": []}
        instrument_set = set(config.INSTRUMENTS.keys())
        for h in headlines[:30]:
            # Try to match ticker symbols in the headline
            found_syms = re.findall(r'\b([A-Z]{2,5})\b', h)
            matched = [s for s in found_syms if s in instrument_set]
            if matched:
                for sym in matched[:2]:
                    label = config.INSTRUMENTS[sym].get("tracks", sym)
                    key = f"{sym} ({label})"
                    grouped.setdefault(key, []).append(h)
            else:
                grouped["Market News (Finviz)"].append(h)

        # Remove empty general bucket
        if not grouped["Market News (Finviz)"]:
            del grouped["Market News (Finviz)"]

        return grouped
    except Exception as e:
        logger.error(f"[sentiment/finviz] fetch error: {e}")
        return {}


def _fetch_yfinance_news() -> dict[str, list[str]]:
    """Fallback: fetch news via yfinance ticker.news."""
    try:
        import yfinance as yf
    except ImportError:
        return {}

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
            logger.warning(f"[sentiment/yfinance] failed for {symbol}: {e}")

    return all_news


def _fetch_rss_news() -> dict[str, list[str]]:
    """Fetch news from public RSS feeds (Google News, CNBC). No API key needed.

    These feeds are the most reliable from inside Docker containers since they
    don't require authentication or special headers.
    """
    import xml.etree.ElementTree as ET

    all_news: dict[str, list[str]] = {}
    session = requests.Session()
    session.headers["User-Agent"] = (
        "Mozilla/5.0 (compatible; TraderAgent/1.0; +https://github.com/trader)"
    )

    for feed_name, url in _RSS_FEEDS.items():
        try:
            resp = session.get(url, timeout=15)
            if not resp.ok:
                logger.warning(f"[sentiment/rss] {feed_name}: HTTP {resp.status_code}")
                continue

            root = ET.fromstring(resp.text)
            headlines = []
            for item in root.findall(".//item"):
                title = item.findtext("title", "").strip()
                if title:
                    # Google News wraps titles with source: "Headline - Source"
                    # Keep it as-is — the source attribution is useful context
                    headlines.append(title)

            if headlines:
                all_news[feed_name] = headlines[:15]
                logger.info(f"[sentiment/rss] {feed_name}: {len(headlines[:15])} headlines")
        except ET.ParseError as e:
            logger.warning(f"[sentiment/rss] {feed_name}: XML parse error: {e}")
        except Exception as e:
            logger.warning(f"[sentiment/rss] {feed_name}: fetch error: {e}")

    # Also fetch instrument-specific news from Google News
    instrument_set = set(config.INSTRUMENTS.keys())
    key_tickers = ["SPY", "QQQ", "DIA", "XLE", "GLD", "TLT"]
    for ticker in key_tickers:
        try:
            label = config.INSTRUMENTS.get(ticker, {}).get("tracks", ticker)
            search_url = f"https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en"
            resp = session.get(search_url, timeout=10)
            if not resp.ok:
                continue
            root = ET.fromstring(resp.text)
            headlines = []
            for item in root.findall(".//item")[:5]:
                title = item.findtext("title", "").strip()
                if title:
                    headlines.append(title)
            if headlines:
                key = f"{ticker} ({label})"
                all_news[key] = headlines
        except Exception:
            pass  # Best-effort per-ticker search

    return all_news


def _fetch_news() -> dict[str, list[str]]:
    """Fetch news from all available sources with priority fallback.

    Returns a merged dict of {label: [headlines]} from whichever sources
    produce data. Tries all sources and merges results.
    """
    all_news: dict[str, list[str]] = {}
    sources_used: list[str] = []

    # 1. Finnhub (best quality, requires API key)
    finnhub = _fetch_finnhub_news()
    if finnhub:
        all_news.update(finnhub)
        sources_used.append("finnhub")

    # 2. Public RSS feeds (Google News, CNBC — no key, works from Docker)
    rss = _fetch_rss_news()
    if rss:
        for key, headlines in rss.items():
            if key in all_news:
                existing = set(all_news[key])
                all_news[key].extend(h for h in headlines if h not in existing)
            else:
                all_news[key] = headlines
        sources_used.append("rss")

    # 3. Finviz RSS (no key, but often 403s from Docker)
    if len(all_news) < 5:
        finviz = _fetch_finviz_news()
        if finviz:
            for key, headlines in finviz.items():
                if key in all_news:
                    existing = set(all_news[key])
                    all_news[key].extend(h for h in headlines if h not in existing)
                else:
                    all_news[key] = headlines
            sources_used.append("finviz")

    # 4. yfinance fallback (only if we got very little from above)
    if len(all_news) < 3:
        yf_news = _fetch_yfinance_news()
        if yf_news:
            for key, headlines in yf_news.items():
                if key not in all_news:
                    all_news[key] = headlines
            sources_used.append("yfinance")

    logger.info(f"[sentiment] News sources used: {', '.join(sources_used) or 'none'} — {sum(len(v) for v in all_news.values())} total headlines")
    return all_news


def _ensure_file():
    """Create sentiment.md with header if it doesn't exist."""
    try:
        with open(config.SENTIMENT_PATH, "r") as f:
            pass
    except FileNotFoundError:
        with open(config.SENTIMENT_PATH, "w") as f:
            f.write("# Sentiment Log\n\nSentiment scores from news headline analysis.\n\n---\n")


# ── Crisis detection ───────────────────────────────────────

import re as _re

_CRISIS_PATTERNS = [
    _re.compile(p, _re.IGNORECASE) for p in [
        r"\b(?:declare[sd]?|enter(?:s|ing)?|launch(?:es|ed)?|start(?:s|ed)?)\s+(?:a\s+)?war\b",
        r"\bmilitary\s+(?:strike|attack|invasion|conflict|action)\b",
        r"\bnuclear\s+(?:strike|threat|attack|weapon)\b",
        r"\bpandemic\s+(?:declared|emergency|outbreak)\b",
        r"\bglobal\s+(?:pandemic|health\s+emergency)\b",
        r"\bsanctions?\s+(?:escalat|expand|broaden|sweeping|massive)\b",
        r"\bembargo\b",
        r"\bdefault(?:s|ed)?\s+on\s+(?:debt|bonds?|treasury|sovereign)\b",
        r"\bsovereign\s+debt\s+crisis\b",
        r"\bbank(?:ing)?\s+(?:collapse|crisis|run|failure|contagion)\b",
        r"\bsystemic\s+(?:risk|crisis|failure|collapse)\b",
        r"\bmarket\s+(?:crash|meltdown|panic|freefall)\b",
        r"\bcircuit\s+breaker(?:s)?\s+(?:triggered|hit|tripped)\b",
        r"\bblack\s+(?:monday|swan|tuesday)\b",
        r"\bmarshall\s+law\b|\bmartial\s+law\b",
        r"\bcoup\s+(?:attempt|d.état)\b",
        r"\bassassinat(?:ion|ed)\b.*(?:president|leader|prime\s+minister)\b",
        r"\bterrorist?\s+attack\b",
    ]
]


def _scan_for_crisis(news: dict[str, list[str]]) -> dict | None:
    """Scan raw headlines for macro crisis signals.

    Returns a crisis alert dict if high-severity patterns are detected,
    or None if headlines look normal.
    """
    matches = []
    for symbol, headlines in news.items():
        for headline in headlines:
            for pattern in _CRISIS_PATTERNS:
                if pattern.search(headline):
                    matches.append({"headline": headline, "symbol": symbol, "pattern": pattern.pattern})
                    break  # one match per headline is enough

    if not matches:
        return None

    # Require at least 2 matching headlines to avoid false positives from
    # a single sensational headline
    if len(matches) < 2:
        logger.info(f"Crisis scan: only {len(matches)} match — below threshold, ignoring")
        return None

    return {
        "timestamp": datetime.now().isoformat(),
        "match_count": len(matches),
        "matches": matches[:10],  # cap stored matches
        "summary": "; ".join(m["headline"][:120] for m in matches[:5]),
    }


def _write_crisis_alert(alert: dict):
    """Write a crisis alert to disk for the risk monitor to pick up."""
    try:
        with open(config.CRISIS_ALERT_PATH, "w") as f:
            json.dump(alert, f, indent=2)
        logger.warning(
            f"🚨 CRISIS ALERT written: {alert['match_count']} headline matches — "
            f"{alert['summary'][:200]}"
        )
    except Exception as e:
        logger.error(f"Failed to write crisis alert: {e}")


def run_sentiment() -> str:
    """Run a sentiment analysis cycle."""
    logger.info("Starting sentiment analysis cycle...")

    _ensure_file()

    news = _fetch_news()
    if not news:
        logger.warning("No news headlines from any source — writing empty cycle note.")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"""
## Sentiment Analysis - {now}

**No news headlines available.** All sources (Finnhub, Finviz, yfinance) returned empty.
This may indicate network issues from the container or API rate limiting.

---
"""
        append_to_file(config.SENTIMENT_PATH, entry)
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
    append_to_file(config.SENTIMENT_PATH, entry)
    logger.info(f"Sentiment analysis saved to {config.SENTIMENT_PATH}")

    # ── Crisis headline scan ───────────────────────────────
    crisis_alert = _scan_for_crisis(news)
    if crisis_alert:
        _write_crisis_alert(crisis_alert)

    return response
