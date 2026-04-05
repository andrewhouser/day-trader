"""Overseas market monitors: Nikkei (Tokyo) and FTSE (London).

These agents run during their respective market windows (all times ET)
and produce structured summaries that downstream U.S. agents consume.

Market sessions (approximate ET equivalents):
  Asia open:        7:30 PM – 10:30 PM ET  (Sun–Thu)
  Asia reopen:     11:30 PM – 2:30 AM ET   (Sun–Thu / Mon–Fri)
  Europe open:      2:30 AM – 5:30 AM ET   (Mon–Fri)
  U.S. premarket:   6:00 AM – 9:30 AM ET   (Mon–Fri)
  U.S. open:        9:30 AM – 4:00 PM ET   (Mon–Fri)

DST notes:
  - Japan does NOT observe DST; ET offsets shift by 1h when U.S. enters EDT.
  - UK observes BST (last Sun in Mar → last Sun in Oct) on different dates
    than the U.S., creating ~2 weeks/year where the offset is off by 1h.
  - Holiday calendars are not yet implemented; agents will run but may
    find no data on exchange holidays.
"""
import json
import logging
from datetime import datetime

import yfinance as yf

import config
from agent import append_to_file, call_ollama, read_recent_entries
from market_data import fetch_index_levels, fetch_instrument_prices
from exchange_calendar import (
    is_exchange_open,
    get_schedule_drift_warning,
    TZ_ET,
)
from overseas_signals import emit_signal, get_pending_signals, format_signals_for_prompt

logger = logging.getLogger(__name__)

# ── Shared helpers ─────────────────────────────────────────

def _get_overseas_model() -> str:
    return config.OVERSEAS_MODEL or config.RESEARCH_MODEL


NIKKEI_SYSTEM = (
    "You are a Japanese equity market analyst monitoring the Tokyo Stock Exchange. "
    "You track the Nikkei 225, sector leadership, yen dynamics, BOJ policy signals, "
    "and macro headlines from Asia. Produce concise, structured summaries that a "
    "U.S.-based trading agent can consume before the American session opens. "
    "Be specific with numbers, levels, and percentage moves."
)

FTSE_SYSTEM = (
    "You are a European equity market analyst monitoring the London Stock Exchange. "
    "You track the FTSE 100, European sector rotation, GBP/EUR dynamics, BOE/ECB "
    "policy signals, and macro headlines from Europe. Produce concise, structured "
    "summaries that a U.S.-based trading agent can consume before the American "
    "session opens. Highlight cross-market handoff conditions. "
    "Be specific with numbers, levels, and percentage moves."
)


# ── Signal detection from ETF price moves ──────────────────

# Maps overseas ETF tickers to their monitor source names
_ASIA_ETFS = {"EWJ": "Japan (Nikkei proxy)"}
_EUROPE_ETFS = {"EWU": "United Kingdom (FTSE proxy)", "EWG": "Germany (DAX proxy)"}


def _detect_etf_signals(
    etf_data: dict,
    source: str,
    etf_map: dict,
    llm_summary: str,
) -> list[dict]:
    """Check ETF price moves against the signal threshold and emit signals.

    Uses yfinance to compare current price vs previous close to detect
    significant overnight/session moves.  The LLM summary is scanned for
    a one-line driver explanation.

    Returns the list of emitted signal dicts.
    """
    emitted = []
    threshold = config.OVERSEAS_SIGNAL_THRESHOLD_PCT

    for ticker, description in etf_map.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2d")
            if hist.empty or len(hist) < 2:
                continue
            prev_close = float(hist["Close"].iloc[-2])
            current = float(hist["Close"].iloc[-1])
            if prev_close == 0:
                continue
            change_pct = ((current - prev_close) / prev_close) * 100

            if abs(change_pct) < threshold:
                continue

            direction = "bullish" if change_pct > 0 else "bearish"
            urgency = "high" if abs(change_pct) >= threshold * 2 else "normal"

            # Try to extract a driver from the LLM summary — fall back to generic
            driver = (
                f"{description} moved {change_pct:+.2f}% overnight. "
                f"See {source} monitor summary for full context."
            )

            suggested = ""
            if direction == "bullish" and change_pct >= threshold * 2:
                suggested = "BUY"
            elif direction == "bearish" and abs(change_pct) >= threshold * 2:
                suggested = "SELL"

            signal = emit_signal(
                source=source,
                ticker=ticker,
                direction=direction,
                move_pct=change_pct,
                driver=driver,
                urgency=urgency,
                suggested_action=suggested,
            )
            emitted.append(signal)
        except Exception as e:
            logger.debug(f"Signal detection failed for {ticker}: {e}")

    return emitted


def _fetch_asia_data() -> dict:
    """Fetch Nikkei 225 and Asia-relevant data points."""
    data: dict = {"indices": {}, "etfs": {}, "news": []}

    # Nikkei 225 index
    try:
        idx = fetch_index_levels()
        for name in ("Nikkei 225",):
            if name in idx:
                data["indices"][name] = idx[name]
    except Exception as e:
        logger.warning(f"Failed to fetch index levels for Asia: {e}")

    # Japan ETF proxy (EWJ)
    asia_tickers = ["EWJ"]
    for sym in asia_tickers:
        try:
            t = yf.Ticker(sym)
            info = t.fast_info
            price = info.get("last_price") or info.get("lastPrice")
            if price:
                data["etfs"][sym] = {"price": round(float(price), 2)}
        except Exception as e:
            logger.debug(f"Failed to fetch {sym}: {e}")

    # News headlines for Japan-related tickers
    for sym in ["EWJ", "^N225"]:
        try:
            t = yf.Ticker(sym)
            news = t.news or []
            for item in news[:5]:
                content = item.get("content", {})
                title = content.get("title", "")
                if title:
                    data["news"].append(title)
        except Exception:
            pass

    return data


def _fetch_europe_data() -> dict:
    """Fetch FTSE 100 and Europe-relevant data points."""
    data: dict = {"indices": {}, "etfs": {}, "news": []}

    try:
        idx = fetch_index_levels()
        for name in ("FTSE 100",):
            if name in idx:
                data["indices"][name] = idx[name]
    except Exception as e:
        logger.warning(f"Failed to fetch index levels for Europe: {e}")

    europe_tickers = ["EWU", "EWG"]
    for sym in europe_tickers:
        try:
            t = yf.Ticker(sym)
            info = t.fast_info
            price = info.get("last_price") or info.get("lastPrice")
            if price:
                data["etfs"][sym] = {"price": round(float(price), 2)}
        except Exception as e:
            logger.debug(f"Failed to fetch {sym}: {e}")

    for sym in ["EWU", "EWG", "^FTSE"]:
        try:
            t = yf.Ticker(sym)
            news = t.news or []
            for item in news[:5]:
                content = item.get("content", {})
                title = content.get("title", "")
                if title:
                    data["news"].append(title)
        except Exception:
            pass

    return data


# ── Nikkei Open Monitor ───────────────────────────────────

def run_nikkei_open() -> str:
    """Monitor Nikkei open conditions and overnight Asia signals.

    Runs during the Tokyo morning session (~7:30 PM – 10:30 PM ET, Sun–Thu).
    Produces a structured summary appended to nikkei_monitor.md.
    """
    logger.info("Starting Nikkei open monitor...")

    # Skip on JPX holidays
    if not is_exchange_open("JPX"):
        logger.info("JPX is closed today (holiday) — skipping Nikkei open monitor.")
        return ""

    # Warn about DST drift
    drift = get_schedule_drift_warning()
    if drift:
        logger.warning(f"DST drift warning: {drift}")

    asia_data = _fetch_asia_data()
    if not asia_data["indices"] and not asia_data["etfs"]:
        logger.warning("No Asia market data available — exchange may be closed.")
        return ""

    # Read previous Nikkei entries for continuity
    prev_entries = read_recent_entries(config.NIKKEI_MONITOR_PATH, 2)

    news_block = "\n".join(f"- {h}" for h in asia_data["news"]) if asia_data["news"] else "No headlines available."

    prompt = f"""Nikkei Open Monitor — {datetime.now().strftime('%Y-%m-%d %H:%M ET')}

### Session: Tokyo Morning (Asia Open)

### Index Data
{json.dumps(asia_data['indices'], indent=2, default=str)}

### Asia ETF Proxies
{json.dumps(asia_data['etfs'], indent=2, default=str)}

### Headlines
{news_block}

### Previous Entries
{prev_entries if prev_entries.strip() else "First entry of the session."}

---

Produce a structured summary covering:
1. **Nikkei 225 Level & Direction** — current level, session change, trend vs prior close
2. **Sector Leadership** — which sectors are leading/lagging in Tokyo
3. **Yen Dynamics** — any notable JPY moves and implications
4. **Macro Headlines** — BOJ signals, trade data, geopolitical developments
5. **Divergence from U.S.** — is Asia confirming or diverging from the prior U.S. close?
6. **Implications for U.S. Session** — key takeaways for the upcoming U.S. trading day
7. **Risk Flags** — anything that could cause overnight volatility

Keep it concise and data-driven. Use bullet points."""

    response = call_ollama(
        prompt,
        system=NIKKEI_SYSTEM,
        model=_get_overseas_model(),
        timeout=config.OVERSEAS_TIMEOUT,
    )

    if response.startswith("[ERROR]"):
        logger.error(f"Nikkei monitor LLM failed: {response}")
        return response

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"""
## Nikkei Open Monitor — {timestamp}
**Session:** Tokyo Morning (Asia Open)

{response}

---
"""
    append_to_file(config.NIKKEI_MONITOR_PATH, entry)
    logger.info(f"Nikkei open monitor saved ({len(response)} chars)")

    # Detect and emit trade signals for significant Asia ETF moves
    signals = _detect_etf_signals(asia_data["etfs"], "nikkei_open", _ASIA_ETFS, response)
    if signals:
        logger.info(f"Nikkei open emitted {len(signals)} trade signal(s)")

    return response


# ── Nikkei Reopen / Asia Continuation Monitor ─────────────

def run_nikkei_reopen() -> str:
    """Monitor Tokyo afternoon session after midday break.

    Runs ~11:30 PM – 2:30 AM ET (Sun–Thu / Mon–Fri).
    Captures changes between Tokyo morning and afternoon sessions
    and updates the Asia summary before Europe opens.
    """
    logger.info("Starting Nikkei reopen / Asia continuation monitor...")

    if not is_exchange_open("JPX"):
        logger.info("JPX is closed today (holiday) — skipping Nikkei reopen monitor.")
        return ""

    drift = get_schedule_drift_warning()
    if drift:
        logger.warning(f"DST drift warning: {drift}")

    asia_data = _fetch_asia_data()
    if not asia_data["indices"] and not asia_data["etfs"]:
        logger.warning("No Asia market data available for reopen session.")
        return ""

    # Read the morning session entry for comparison
    morning_entries = read_recent_entries(config.NIKKEI_MONITOR_PATH, 3)

    news_block = "\n".join(f"- {h}" for h in asia_data["news"]) if asia_data["news"] else "No headlines available."

    prompt = f"""Nikkei Reopen Monitor — {datetime.now().strftime('%Y-%m-%d %H:%M ET')}

### Session: Tokyo Afternoon (Asia Continuation)

### Index Data
{json.dumps(asia_data['indices'], indent=2, default=str)}

### Asia ETF Proxies
{json.dumps(asia_data['etfs'], indent=2, default=str)}

### Headlines
{news_block}

### Morning Session Summary
{morning_entries if morning_entries.strip() else "No morning session data."}

---

Compare the afternoon session to the morning session and produce:
1. **Session Change** — how has the Nikkei moved since the midday break?
2. **Momentum Shift** — did the afternoon session confirm or reverse morning trends?
3. **Late-Breaking Developments** — any new macro/geopolitical headlines since morning
4. **Updated Asia Summary** — consolidated view for European and U.S. agents
5. **Handoff to Europe** — what should the FTSE monitor watch for based on Asia's close?

Keep it concise. Focus on what changed since the morning session."""

    response = call_ollama(
        prompt,
        system=NIKKEI_SYSTEM,
        model=_get_overseas_model(),
        timeout=config.OVERSEAS_TIMEOUT,
    )

    if response.startswith("[ERROR]"):
        logger.error(f"Nikkei reopen monitor LLM failed: {response}")
        return response

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"""
## Nikkei Reopen Monitor — {timestamp}
**Session:** Tokyo Afternoon (Asia Continuation)

{response}

---
"""
    append_to_file(config.NIKKEI_MONITOR_PATH, entry)
    logger.info(f"Nikkei reopen monitor saved ({len(response)} chars)")

    # Detect and emit trade signals for significant Asia ETF moves
    signals = _detect_etf_signals(asia_data["etfs"], "nikkei_reopen", _ASIA_ETFS, response)
    if signals:
        logger.info(f"Nikkei reopen emitted {len(signals)} trade signal(s)")

    return response


# ── FTSE Open Monitor ─────────────────────────────────────

def run_ftse_open() -> str:
    """Monitor FTSE / London open conditions and Europe-at-open market tone.

    Runs ~2:30 AM – 5:30 AM ET (Mon–Fri).
    Consumes the latest Asia summary to provide cross-market context.
    Produces a structured summary for U.S. premarket agents.
    """
    logger.info("Starting FTSE open monitor...")

    if not is_exchange_open("LSE"):
        logger.info("LSE is closed today (holiday) — skipping FTSE open monitor.")
        return ""

    drift = get_schedule_drift_warning()
    if drift:
        logger.warning(f"DST drift warning: {drift}")

    europe_data = _fetch_europe_data()
    if not europe_data["indices"] and not europe_data["etfs"]:
        logger.warning("No Europe market data available — exchange may be closed.")
        return ""

    # Read Asia overnight summary for cross-market context
    asia_summary = read_recent_entries(config.NIKKEI_MONITOR_PATH, 3)

    # Read previous FTSE entries for continuity
    prev_entries = read_recent_entries(config.FTSE_MONITOR_PATH, 2)

    news_block = "\n".join(f"- {h}" for h in europe_data["news"]) if europe_data["news"] else "No headlines available."

    prompt = f"""FTSE Open Monitor — {datetime.now().strftime('%Y-%m-%d %H:%M ET')}

### Session: London Open (Europe)

### Index Data
{json.dumps(europe_data['indices'], indent=2, default=str)}

### Europe ETF Proxies
{json.dumps(europe_data['etfs'], indent=2, default=str)}

### Headlines
{news_block}

### Asia Overnight Summary
{asia_summary if asia_summary.strip() else "No Asia data available."}

### Previous FTSE Entries
{prev_entries if prev_entries.strip() else "First entry of the session."}

---

Produce a structured summary covering:
1. **FTSE 100 Level & Direction** — current level, session change, gap from prior close
2. **European Sector Rotation** — which sectors are leading/lagging at the open
3. **GBP/EUR Dynamics** — notable currency moves and implications
4. **Macro Headlines** — BOE/ECB signals, economic data releases, political developments
5. **Asia-to-Europe Handoff** — did Europe confirm or diverge from Asia's overnight tone?
6. **U.S. Premarket Implications** — key themes for the upcoming U.S. session
7. **Cross-Market Risk Flags** — overnight volatility, gap risks, event catalysts

Keep it concise and data-driven. Use bullet points."""

    response = call_ollama(
        prompt,
        system=FTSE_SYSTEM,
        model=_get_overseas_model(),
        timeout=config.OVERSEAS_TIMEOUT,
    )

    if response.startswith("[ERROR]"):
        logger.error(f"FTSE monitor LLM failed: {response}")
        return response

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"""
## FTSE Open Monitor — {timestamp}
**Session:** London Open (Europe)

{response}

---
"""
    append_to_file(config.FTSE_MONITOR_PATH, entry)
    logger.info(f"FTSE open monitor saved ({len(response)} chars)")

    # Detect and emit trade signals for significant Europe ETF moves
    signals = _detect_etf_signals(europe_data["etfs"], "ftse_open", _EUROPE_ETFS, response)
    if signals:
        logger.info(f"FTSE open emitted {len(signals)} trade signal(s)")

    return response


# ── Europe Handoff Summary ─────────────────────────────────

HANDOFF_SYSTEM = (
    "You are a cross-market analyst producing a pre-market briefing for a "
    "U.S.-based trading agent. You synthesize overnight Asia and European "
    "market data into a single, actionable summary. Focus on themes that "
    "will affect U.S. equities, sectors, and risk sentiment at the open. "
    "Be concise, specific with numbers, and highlight divergences."
)


def run_europe_handoff() -> str:
    """Synthesize Asia + Europe overnight data into a single pre-market brief.

    Runs once at ~5:30 AM ET (Mon–Fri), after the FTSE monitor has
    produced its initial entries.  The output is a consolidated summary
    that the Morning Report and Market Check can consume directly,
    reducing their context window compared to reading both raw feeds.
    """
    logger.info("Starting Europe Handoff Summary...")

    # Read the full overnight feeds
    asia_entries = read_recent_entries(config.NIKKEI_MONITOR_PATH, 5)
    europe_entries = read_recent_entries(config.FTSE_MONITOR_PATH, 3)

    if not asia_entries.strip() and not europe_entries.strip():
        logger.info("No overseas data available — skipping handoff summary.")
        return ""

    # Include DST drift context if relevant
    drift = get_schedule_drift_warning()
    drift_note = f"\n**DST Note:** {drift}" if drift else ""

    # Include any pending overseas trade signals
    pending_signals = get_pending_signals()
    signals_block = ""
    if pending_signals:
        signals_block = f"""

### Pending Overseas Trade Signals
The following trade signals were emitted by overnight monitors and are awaiting
evaluation by the U.S. trading agent:

{format_signals_for_prompt(pending_signals)}
"""

    prompt = f"""Europe Handoff Summary — {datetime.now().strftime('%Y-%m-%d %H:%M ET')}

You are producing the final pre-market briefing before the U.S. session opens.
Synthesize the overnight Asia and European market data below into a single
actionable summary for the U.S. trading agent.

### Asia Overnight (Nikkei / Tokyo)
{asia_entries if asia_entries.strip() else "No Asia data available."}

### Europe at Open (FTSE / London)
{europe_entries if europe_entries.strip() else "No Europe data available."}
{drift_note}
{signals_block}
---

Produce a consolidated pre-market brief with these sections:

1. **Overnight Narrative** — one paragraph summarizing the dominant theme across Asia and Europe
2. **Key Levels** — Nikkei close, FTSE current, notable moves in EWJ/EWU/EWG
3. **Sector Signals** — which global sectors are leading/lagging and what that implies for U.S. sector ETFs
4. **Macro & Policy** — BOJ/BOE/ECB signals, economic data, currency moves (JPY, GBP, EUR)
5. **Risk Flags** — overnight volatility, gap risks, geopolitical catalysts
6. **U.S. Session Setup** — 3-5 bullet points on what the U.S. trading agent should watch for at the open
7. **Cross-Market Divergences** — where Asia and Europe disagreed, and what that means
8. **Overseas Signal Assessment** — for each pending trade signal, provide your assessment of whether the signal is supported by the overnight data, any caveats, and whether the U.S. agent should prioritize it

Keep it tight. This is the single document the U.S. agents will read for overnight context."""

    response = call_ollama(
        prompt,
        system=HANDOFF_SYSTEM,
        model=_get_overseas_model(),
        timeout=config.OVERSEAS_TIMEOUT,
    )

    if response.startswith("[ERROR]"):
        logger.error(f"Europe Handoff Summary LLM failed: {response}")
        return response

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"""
## Europe Handoff Summary — {timestamp}

{response}

---
"""
    append_to_file(config.HANDOFF_SUMMARY_PATH, entry)
    logger.info(f"Europe Handoff Summary saved ({len(response)} chars)")
    return response


# ── Convenience: read latest summaries for downstream agents ──

def get_asia_summary(max_entries: int = 3) -> str:
    """Read the latest Asia/Nikkei monitor entries for downstream consumption."""
    return read_recent_entries(config.NIKKEI_MONITOR_PATH, max_entries)


def get_europe_summary(max_entries: int = 3) -> str:
    """Read the latest Europe/FTSE monitor entries for downstream consumption."""
    return read_recent_entries(config.FTSE_MONITOR_PATH, max_entries)


def get_handoff_summary(max_entries: int = 1) -> str:
    """Read the latest Europe Handoff Summary for downstream consumption."""
    return read_recent_entries(config.HANDOFF_SUMMARY_PATH, max_entries)
