"""Core trading agent that interfaces with Ollama for reasoning."""
import json
import logging
import re
import threading
from datetime import datetime

import requests

import config
from market_data import (
    get_market_summary,
    get_technicals_summary,
    fetch_technical_indicators,
    get_vix_term_structure_summary,
    get_correlation_summary,
)
from regime import detect_regime, get_regime_summary, load_regime
from position_sizing import get_sizing_summary

logger = logging.getLogger(__name__)

# Thread-local storage so call_ollama knows which task is running and
# can bail out early when a stop is requested.
_thread_local = threading.local()


class TaskCancelledError(Exception):
    """Raised when a task's stop flag is set."""


def set_current_task_id(task_id: str | None):
    """Set the task_id for the current thread (called by scheduler/API wrappers)."""
    _thread_local.task_id = task_id


def call_ollama(
    prompt: str,
    system: str = config.SYSTEM_PROMPT,
    model: str | None = None,
    timeout: int | None = None,
    temperature: float | None = None,
) -> str:
    """Send a prompt to Ollama and return the response text.

    Args:
        temperature: Override config.TEMPERATURE for this call.  Used by the
                     confidence-gated temperature system so the trading agent
                     explores more freely when no high-confidence playbook
                     patterns apply.
    """
    # Check cancellation before the (potentially very long) HTTP call
    task_id = getattr(_thread_local, "task_id", None)
    if task_id:
        try:
            from api import is_task_cancelled
            if is_task_cancelled(task_id):
                raise TaskCancelledError(f"Task {task_id} was cancelled")
        except ImportError:
            pass

    url = f"{config.OLLAMA_BASE_URL}/api/generate"
    resolved_model = model or config.TRADER_MODEL_NAME
    resolved_temp = temperature if temperature is not None else config.TEMPERATURE
    payload = {
        "model": resolved_model,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "temperature": resolved_temp,
            # Disable Qwen3 extended thinking for non-reasoning tasks; has no
            # effect on other model families (deepseek-r1, llama, phi3, etc.)
            "think": resolved_model == config.TRADER_MODEL_NAME,
        },
    }
    try:
        resp = requests.post(url, json=payload, timeout=timeout if timeout is not None else config.OLLAMA_TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("response", "")
    except requests.exceptions.RequestException as e:
        logger.error(f"Ollama request failed: {e}")
        return f"[ERROR] Could not reach Ollama: {e}"


def load_portfolio() -> dict:
    """Load portfolio state from disk."""
    with open(config.PORTFOLIO_PATH, "r") as f:
        return json.load(f)


def save_portfolio(portfolio: dict):
    """Save portfolio state to disk and record a history snapshot."""
    portfolio["last_updated"] = datetime.now().isoformat()
    with open(config.PORTFOLIO_PATH, "w") as f:
        json.dump(portfolio, f, indent=2)
    _record_portfolio_snapshot(portfolio)


def _record_portfolio_snapshot(portfolio: dict):
    """Append a timestamped snapshot to portfolio_history.json."""
    snapshot = {
        "timestamp": portfolio["last_updated"],
        "total_value_usd": portfolio["total_value_usd"],
        "cash_usd": portfolio["cash_usd"],
    }
    try:
        with open(config.PORTFOLIO_HISTORY_PATH, "r") as f:
            history = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        history = []
    history.append(snapshot)
    with open(config.PORTFOLIO_HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2)


def read_recent_entries(filepath: str, max_entries: int = config.MAX_RECENT_ENTRIES) -> str:
    """Read the most recent N entries from a markdown log file.
    Entries are separated by '---' lines."""
    try:
        with open(filepath, "r") as f:
            content = f.read()
    except FileNotFoundError:
        return ""

    sections = content.split("\n---\n")
    # Keep header (first section) + last N entries
    if len(sections) <= max_entries + 1:
        return content
    header = sections[0]
    recent = sections[-(max_entries):]
    return header + "\n---\n" + "\n---\n".join(recent)


def append_to_file(filepath: str, content: str):
    """Append content to a file."""
    with open(filepath, "a") as f:
        f.write(content)


def parse_trades_from_response(response: str, portfolio: dict) -> list[dict]:
    """Parse structured JSON trade blocks from the LLM response."""
    json_pattern = r'```json\s*(.*?)\s*```'
    matches = re.findall(json_pattern, response, re.DOTALL)

    trades = []
    for match in matches:
        try:
            data = json.loads(match)
            if isinstance(data, dict) and "action" in data:
                trades.append(data)
            elif isinstance(data, list):
                trades.extend([t for t in data if isinstance(t, dict) and "action" in t])
        except json.JSONDecodeError:
            continue

    return trades


def validate_trade(trade: dict, portfolio: dict) -> tuple[bool, str]:
    """Validate a trade against risk rules."""
    action = trade.get("action", "").upper()
    ticker = trade.get("ticker", "")
    quantity = trade.get("quantity", 0)
    price = trade.get("price", 0)

    if ticker not in config.INSTRUMENTS:
        return False, f"Instrument {ticker} not in allowed scope"

    # Get regime-adjusted max position size
    regime_data = load_regime()
    regime_params = regime_data.get("parameters", {})
    max_pct = regime_params.get("max_position_pct", config.MAX_POSITION_PCT)

    if action == "BUY":
        cost = quantity * price
        if cost > portfolio["cash_usd"]:
            return False, f"Insufficient cash: need ${cost:.2f}, have ${portfolio['cash_usd']:.2f}"
        max_allowed = portfolio["total_value_usd"] * max_pct
        existing_value = 0
        for pos in portfolio["positions"]:
            if pos["ticker"] == ticker:
                existing_value = pos["quantity"] * pos["current_price"]
        if existing_value + cost > max_allowed:
            return False, f"Position would exceed {max_pct*100:.0f}% limit (${max_allowed:.2f})"

    elif action == "SELL":
        position = None
        for pos in portfolio["positions"]:
            if pos["ticker"] == ticker:
                position = pos
                break
        if not position:
            return False, f"No open position in {ticker}"
        if quantity > position["quantity"]:
            return False, f"Cannot sell {quantity} shares, only hold {position['quantity']}"
    else:
        return False, f"Unknown action: {action}"

    return True, "OK"


def execute_trade(trade: dict, portfolio: dict, technicals: dict | None = None) -> tuple[dict, bool]:
    """Execute a validated trade and update portfolio.
    Returns (updated_portfolio, position_was_closed).

    Args:
        trade: Trade dict with action, ticker, quantity, price, reasoning.
        portfolio: Current portfolio state.
        technicals: Technical indicators dict (for ATR-based stops on new positions).
    """
    action = trade["action"].upper()
    ticker = trade["ticker"]
    quantity = trade["quantity"]
    price = trade["price"]
    reasoning = trade.get("reasoning", "No reasoning provided")
    now = datetime.now()
    position_closed = False

    # Get ATR for stop calculation
    atr = None
    if technicals:
        ticker_data = technicals.get(ticker, {})
        atr = ticker_data.get("atr_14")

    # Get regime params for stop multiplier
    regime_data = load_regime()
    regime_params = regime_data.get("parameters", {})
    initial_stop_mult = config.INITIAL_STOP_ATR_MULTIPLIER
    trailing_stop_mult = regime_params.get("stop_atr_multiplier", config.TRAILING_STOP_ATR_MULTIPLIER)

    if action == "BUY":
        cost = quantity * price
        portfolio["cash_usd"] -= cost
        portfolio["cash_usd"] = round(portfolio["cash_usd"], 2)

        existing = None
        for pos in portfolio["positions"]:
            if pos["ticker"] == ticker:
                existing = pos
                break

        if existing:
            total_qty = existing["quantity"] + quantity
            avg_price = ((existing["quantity"] * existing["entry_price"]) + cost) / total_qty
            existing["quantity"] = total_qty
            existing["entry_price"] = round(avg_price, 2)
            existing["current_price"] = price
            existing["unrealized_pnl"] = round((price - avg_price) * total_qty, 2)
            existing["notes"] += f" | Added {quantity} @ ${price} on {now.strftime('%Y-%m-%d')}"
            # Update stops based on new average
            if atr:
                existing["initial_stop"] = round(avg_price - initial_stop_mult * atr, 2)
                existing["trailing_stop"] = round(
                    max(existing.get("highest_since_entry", price), price) - trailing_stop_mult * atr, 2
                )
        else:
            initial_stop = round(price - initial_stop_mult * atr, 2) if atr else None
            trailing_stop = round(price - trailing_stop_mult * atr, 2) if atr else None
            portfolio["positions"].append({
                "ticker": ticker,
                "instrument_type": config.INSTRUMENTS[ticker]["type"],
                "quantity": quantity,
                "entry_price": price,
                "entry_date": now.isoformat(),
                "current_price": price,
                "unrealized_pnl": 0.0,
                "notes": reasoning[:200],
                "initial_stop": initial_stop,
                "trailing_stop": trailing_stop,
                "highest_since_entry": price,
                "take_profit_partial_hit": False,
            })

    elif action == "SELL":
        for i, pos in enumerate(portfolio["positions"]):
            if pos["ticker"] == ticker:
                proceeds = quantity * price
                portfolio["cash_usd"] += proceeds
                portfolio["cash_usd"] = round(portfolio["cash_usd"], 2)

                realized_pnl = round((price - pos["entry_price"]) * quantity, 2)
                trade["realized_pnl"] = realized_pnl
                # Stash the original entry price so strategy scoring has the
                # correct cost basis after the position is removed from the list.
                trade["_entry_price"] = pos["entry_price"]

                if quantity >= pos["quantity"]:
                    portfolio["positions"].pop(i)
                    position_closed = True
                else:
                    pos["quantity"] -= quantity
                    pos["current_price"] = price
                    pos["unrealized_pnl"] = round(
                        (price - pos["entry_price"]) * pos["quantity"], 2
                    )
                break

    # Update portfolio totals
    total_positions_value = sum(
        p["quantity"] * p["current_price"] for p in portfolio["positions"]
    )
    portfolio["total_value_usd"] = round(portfolio["cash_usd"] + total_positions_value, 2)
    portfolio["trade_count"] += 1
    portfolio["all_time_high"] = max(portfolio["all_time_high"], portfolio["total_value_usd"])
    portfolio["all_time_low"] = min(portfolio["all_time_low"], portfolio["total_value_usd"])

    # Log the trade
    entry_scores = trade.get("entry_scores")
    scores_line = ""
    if entry_scores:
        scores_line = f"- **Entry Scores:** {json.dumps(entry_scores)}\n"

    # Hypothesis lines (structured trade thesis for later reflection evaluation)
    hypothesis = trade.get("hypothesis", "")
    falsified_by = trade.get("falsified_by", "")
    confidence = trade.get("confidence", "")
    horizon = trade.get("horizon", "")
    hyp_lines = ""
    if hypothesis:
        hyp_lines += f"- **Hypothesis:** {hypothesis}\n"
    if falsified_by:
        hyp_lines += f"- **Falsified By:** {falsified_by}\n"
    if confidence:
        hyp_lines += f"- **Confidence:** {confidence}\n"
    if horizon:
        hyp_lines += f"- **Horizon:** {horizon}\n"

    # Strategy classification
    from strategy_tracker import classify_trade_strategy
    strategy = classify_trade_strategy(reasoning)
    strategy_line = f"- **Strategy:** {strategy}\n"

    # Update strategy scores for closed SELL trades
    if action == "SELL" and trade.get("realized_pnl") is not None:
        from strategy_tracker import update_strategy_scores
        # Use _entry_price stashed in the SELL branch above — NOT the sell price.
        entry_price_for_scoring = trade.get("_entry_price", price)
        update_strategy_scores(strategy, trade["realized_pnl"], entry_price_for_scoring, quantity)

    log_entry = f"""
## {action} - {ticker}
- **Date:** {now.strftime('%Y-%m-%d %H:%M:%S')}
- **Action:** {action}
- **Instrument:** {ticker} ({config.INSTRUMENTS[ticker]['tracks']})
- **Quantity:** {quantity}
- **Price:** ${price}
- **Total:** ${quantity * price:.2f}
{f'- **Realized P&L:** ${trade.get("realized_pnl", 0):.2f}' if action == 'SELL' else ''}{scores_line}{strategy_line}{hyp_lines}- **Reasoning:** {reasoning}
- **Portfolio Balance:** ${portfolio['total_value_usd']:.2f}

---
"""
    append_to_file(config.TRADE_LOG_PATH, log_entry)
    save_portfolio(portfolio)

    return portfolio, position_closed


def _check_stop_loss_and_opportunities(portfolio: dict, instruments: dict) -> list[dict]:
    """Check positions for stop-loss breaches and instruments for opportunity surges.
    Returns a list of alert dicts describing what was detected."""
    from market_data import fetch_instrument_prices

    alerts = []

    # Check existing positions for stop-loss
    for pos in portfolio.get("positions", []):
        ticker = pos["ticker"]
        entry_price = pos["entry_price"]
        instrument_data = instruments.get(ticker, {})
        current_price = instrument_data.get("price")
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
            })

    # Check all instruments for opportunity surges (big intraday move up)
    for ticker, data in instruments.items():
        if "error" in data or data.get("change_pct") is None:
            continue
        if data["change_pct"] >= config.OPPORTUNITY_PCT:
            alerts.append({
                "type": "opportunity",
                "ticker": ticker,
                "price": data["price"],
                "change_pct": data["change_pct"],
                "five_day_change_pct": data.get("five_day_change_pct", 0),
            })

    return alerts


def _run_bear_case_debate(trade: dict, market_context_snippet: str) -> tuple[bool, str]:
    """Run an adversarial bear-case analysis for a proposed trade.

    Called before executing trades whose cost exceeds BEAR_CASE_THRESHOLD_PCT
    of portfolio value.  The bear-case model argues the strongest case AGAINST
    the trade; the result is returned so the caller can log it and decide.

    Returns:
        (proceed: bool, bear_case_text: str)
        proceed is always True — the final decision is left to the trading agent's
        original reasoning.  The bear case is logged in the trade entry so the
        agent can learn from cases where it ignored valid counter-arguments.
    """
    ticker = trade.get("ticker", "")
    action = trade.get("action", "")
    quantity = trade.get("quantity", 0)
    price = trade.get("price", 0)
    reasoning = trade.get("reasoning", "No reasoning provided")
    hypothesis = trade.get("hypothesis", "")

    bear_prompt = f"""A trading agent has proposed the following trade:

Action: {action}
Instrument: {ticker}
Quantity: {quantity} shares @ ${price}
Cost: ${quantity * price:.2f}

Agent's reasoning:
{reasoning}

Agent's hypothesis:
{hypothesis if hypothesis else "No formal hypothesis stated."}

Current market context:
{market_context_snippet[:800]}

---

Your job is to argue the STRONGEST POSSIBLE CASE AGAINST this trade.  Be specific
and quantitative.  Do not be contrarian for its own sake — only raise objections
that are grounded in the data above.

Address:
1. What technical or fundamental signals contradict the thesis?
2. What is the most likely failure scenario, and how probable is it?
3. Is the entry timing poor relative to indicators (RSI stretched, approaching resistance, etc.)?
4. Does the position add concentration or correlation risk to the existing portfolio?
5. Is there an upcoming event (earnings, Fed, economic release) that creates asymmetric downside?
6. What would a prudent risk manager say about this trade?

Be direct.  Rate the strength of the bear case: STRONG / MODERATE / WEAK."""

    logger.info(f"Running bear-case debate for {action} {ticker}...")
    bear_case = call_ollama(
        bear_prompt,
        system=(
            "You are a skeptical risk analyst whose job is to find flaws in proposed trades. "
            "You are not trying to be helpful — you are trying to prevent bad trades. "
            "Be blunt, specific, and grounded in data."
        ),
        model=config.RESEARCH_MODEL,
        timeout=config.OLLAMA_TIMEOUT,
    )
    logger.info(f"Bear case received for {ticker} ({len(bear_case)} chars)")
    return True, bear_case


def run_research():
    """Run a dedicated research cycle using the multi-source research engine.

    Stages:
    1. Run the multi-source pipeline (FRED, Finnhub, SEC EDGAR, Alpha Vantage,
       Finviz, Reuters, Investing.com) to gather and normalize data.
    2. Feed the structured research data + market prices into the LLM for synthesis.
    3. Save both the machine-readable JSON report and the human-readable brief.
    4. Check for stop-loss / opportunity alerts and invoke the trader if needed.
    """
    logger.info("Starting multi-source research cycle...")

    # ── 1. Run multi-source pipeline ───────────────────────
    from research.pipeline import run_pipeline
    from research.summarizer import generate_human_summary

    report = run_pipeline(use_cache=config.RESEARCH_CACHE_ENABLED)
    logger.info(
        f"Pipeline returned {len(report.all_items)} items, "
        f"{len(report.top_narratives)} narratives"
    )

    # ── 2. Generate human summary via LLM ──────────────────
    human_summary = generate_human_summary(report)
    report.human_summary = human_summary

    # ── 3. Save outputs ───────────────────────────────────
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    date_str = now.strftime("%Y-%m-%d")

    # Save machine-readable JSON
    try:
        report_dict = report.to_dict()
        with open(config.MARKET_RESEARCH_PATH, "w") as f:
            json.dump(report_dict, f, indent=2, default=str)
        logger.info(f"JSON report saved to {config.MARKET_RESEARCH_PATH}")
    except Exception as e:
        logger.error(f"Failed to save JSON report: {e}")

    # Save human-readable brief
    try:
        with open(config.MARKET_BRIEF_PATH, "w") as f:
            f.write(f"# Market Research Brief — {timestamp}\n\n{human_summary}")
        logger.info(f"Market brief saved to {config.MARKET_BRIEF_PATH}")
    except Exception as e:
        logger.error(f"Failed to save market brief: {e}")

    # Also build a combined research note for the existing research.md log
    # (preserves backward compatibility with the trader agent's prompt)
    market_summary = get_market_summary()
    portfolio = load_portfolio()
    held_tickers = [p["ticker"] for p in portfolio["positions"]]
    all_tickers = list(config.INSTRUMENTS.keys())
    recent_reflections = read_recent_entries(config.REFLECTIONS_PATH, 5)

    # Build narrative context for the LLM research note
    narrative_context = ""
    for i, cluster in enumerate(report.top_narratives[:6], 1):
        sources = ", ".join({item.source for item in cluster.items})
        narrative_context += (
            f"{i}. {cluster.label} — {cluster.aggregate_sentiment.value} "
            f"(influence: {cluster.influence_score}, sources: {sources})\n"
        )

    macro_context = ""
    for item in report.top_macro_releases[:5]:
        macro_context += f"- [{item.source}] {item.summary}\n"

    filings_context = ""
    for item in report.top_company_catalysts[:5]:
        filings_context += f"- [{item.source}] {item.summary}\n"

    prompt = f"""Market Research Task — Multi-Source Analysis

You are conducting your regular research cycle. You now have access to data from
multiple sources: FRED, Finnhub, SEC EDGAR, Alpha Vantage, Finviz, Reuters, and
Investing.com. Use this multi-source data to produce a structured research note.

{market_summary}

### Multi-Source Research Data

#### Top Market Narratives (from {len(report.all_items)} items across {len(set(i.source for i in report.all_items))} sources)
{narrative_context or "No significant narratives detected."}

#### Key Macro Data (primary sources: FRED, BLS)
{macro_context or "No macro releases in this cycle."}

#### Notable SEC Filings
{filings_context or "No notable filings."}

#### Risk Factors
{chr(10).join(f'- {r}' for r in report.risk_factors) or "None identified."}

#### Bullish Factors
{chr(10).join(f'- {b}' for b in report.bullish_factors) or "None identified."}

#### Bearish Factors
{chr(10).join(f'- {b}' for b in report.bearish_factors) or "None identified."}

### Your Current Positions
{json.dumps(held_tickers) if held_tickers else "None — fully in cash."}

### Instruments In Scope
{', '.join(all_tickers)}

### Recent Reflections
{recent_reflections}

---

Produce a research note with the following sections:

1. **Market Regime Assessment**
   - Is the overall market trending up, down, or sideways?
   - What is the current volatility environment?
   - Are there any divergences between U.S. and international markets?
   - What do the multi-source narratives tell us about the current regime?

2. **Sector & Instrument Analysis**
   - For each instrument in scope, briefly assess: current trend, momentum, and
     whether it looks attractive, neutral, or risky right now.
   - Reference specific data from FRED, Finnhub, or other sources where relevant.

3. **Key Risks & Catalysts**
   - What macro events, earnings, or data releases could move markets in the next 24h?
   - What are the biggest risks to your current positions (if any)?
   - Note any SEC filings or official releases that are relevant.

4. **Watchlist & Opportunities**
   - Which instruments are you most interested in for potential trades?
   - What specific price levels or conditions would trigger a buy or sell?

5. **Source Confidence Assessment**
   - Which sources provided the most useful data this cycle?
   - Are there any conflicting signals between primary and secondary sources?
   - Note any sources that were unavailable or returned empty data.

6. **Summary Thesis**
   - In 2-3 sentences, state your current market thesis and how it should
     influence your next trading decision.

Think step by step. Be specific with numbers and levels. Cite sources.
This note will be read before your next hourly trading check."""

    logger.info("Sending multi-source research prompt to LLM...")
    response = call_ollama(prompt, model=config.RESEARCH_MODEL, timeout=config.RESEARCH_TIMEOUT)
    logger.info(f"Research response received ({len(response)} chars)")

    # Save research note to the existing log
    research_entry = f"""
## Research Note (Multi-Source) - {timestamp}

{response}

---
"""
    append_to_file(config.RESEARCH_PATH, research_entry)

    # Also save a dated snapshot
    snapshot_path = f"{config.REPORTS_DIR}/{date_str}_research.md"
    with open(snapshot_path, "w") as f:
        f.write(f"# Research Note - {date_str}\n\n{response}")

    logger.info(f"Research note saved to {config.RESEARCH_PATH} and {snapshot_path}")

    # ── 4. Check for stop-loss / opportunity alerts ────────
    from market_data import fetch_instrument_prices
    instruments = fetch_instrument_prices()
    portfolio = load_portfolio()  # reload in case it changed
    alerts = _check_stop_loss_and_opportunities(portfolio, instruments)

    if alerts:
        alert_descriptions = []
        for a in alerts:
            if a["type"] == "stop_loss":
                alert_descriptions.append(
                    f"STOP-LOSS: {a['ticker']} has dropped {a['drop_pct']}% "
                    f"from entry ${a['entry_price']} to ${a['current_price']}"
                )
            elif a["type"] == "opportunity":
                alert_descriptions.append(
                    f"OPPORTUNITY: {a['ticker']} is up {a['change_pct']}% today "
                    f"at ${a['price']} (5d: {a['five_day_change_pct']:+.2f}%)"
                )

        alert_summary = "\n".join(alert_descriptions)
        logger.warning(
            f"Research detected {len(alerts)} alert(s) — invoking trader:\n{alert_summary}"
        )

        alert_entry = f"""
## ⚠️ Research Alert - {timestamp}
The following conditions were detected during research and triggered an immediate trading review:

{alert_summary}

---
"""
        append_to_file(config.RESEARCH_PATH, alert_entry)
        run_hourly_check()
    else:
        logger.info("No stop-loss or opportunity alerts detected this research cycle.")

    return response


def run_hourly_check():
    """Execute the market check and trading cycle."""

    def _get_weights_for_prompt() -> str:
        try:
            from score_weights import get_weights_summary
            return get_weights_summary()
        except Exception:
            return "No learned weights yet — all dimensions weighted equally at 1.0."

    logger.info("Starting market check...")

    # 1. Fetch market data and compute technicals
    market_summary = get_market_summary()
    logger.info("Market data fetched")

    technicals = fetch_technical_indicators()
    technicals_summary = get_technicals_summary()
    logger.info("Technical indicators computed")

    # 1a. Richer market structure indicators
    vix_summary = get_vix_term_structure_summary()
    correlation_summary = get_correlation_summary(lookback_days=30)
    logger.info("VIX term structure and correlation matrix computed")

    # 2. Detect market regime
    regime_data = detect_regime(technicals)
    regime_summary = get_regime_summary()
    regime_params = regime_data.get("parameters", {})
    logger.info(f"Market regime: {regime_data.get('regime', 'UNKNOWN')}")

    # 3. Load portfolio and recent context
    portfolio = load_portfolio()
    recent_reflections = read_recent_entries(config.REFLECTIONS_PATH, 5)
    recent_trades = read_recent_entries(config.TRADE_LOG_PATH, 10)

    # Read all recent research
    recent_research = read_recent_entries(config.RESEARCH_PATH, 10)

    # Read sentiment and events context
    recent_sentiment = read_recent_entries(config.SENTIMENT_PATH, 3)
    try:
        with open(config.EVENTS_PATH, "r") as f:
            events_calendar = f.read()[-2000:]
    except FileNotFoundError:
        events_calendar = ""
    recent_risk_alerts = read_recent_entries(config.RISK_ALERTS_PATH, 5)

    # Read overseas monitor summaries for cross-market context
    # Prefer the consolidated handoff summary when available
    handoff_summary = read_recent_entries(config.HANDOFF_SUMMARY_PATH, 1)
    asia_summary = read_recent_entries(config.NIKKEI_MONITOR_PATH, 2)
    europe_summary = read_recent_entries(config.FTSE_MONITOR_PATH, 2)

    # 3a. Rolling 30-day market context
    from market_context import get_market_context_for_prompt
    rolling_context = get_market_context_for_prompt()

    # 3b. Strategy playbook and score ladder
    from playbook_agent import get_playbook_context
    from strategy_tracker import get_strategy_ladder, get_suspended_strategies
    playbook_context = get_playbook_context(max_chars=2500)
    strategy_ladder = get_strategy_ladder()
    suspended_strategies = get_suspended_strategies()

    # 4. Compute position sizing recommendations
    sizing_summary = get_sizing_summary(technicals, portfolio["total_value_usd"], regime_params)

    # 5. Load quantitative feedback
    from performance_analyst import get_performance_feedback
    perf_feedback = get_performance_feedback()

    # 5a. Confidence-gated temperature — exploit known patterns vs. explore novel ones
    from playbook_agent import get_adaptive_temperature
    adaptive_temp = get_adaptive_temperature()
    logger.info(f"Adaptive temperature: {adaptive_temp} (default: {config.TEMPERATURE})")

    # 6. Build prompt
    all_instruments = list(config.INSTRUMENTS.keys())
    instrument_details = json.dumps(config.INSTRUMENTS, indent=2)

    # Build stop/target info for existing positions
    stops_info = ""
    for pos in portfolio.get("positions", []):
        t = pos["ticker"]
        stops_info += (
            f"- {t}: entry=${pos['entry_price']}, "
            f"initial_stop=${pos.get('initial_stop', 'N/A')}, "
            f"trailing_stop=${pos.get('trailing_stop', 'N/A')}, "
            f"highest=${pos.get('highest_since_entry', 'N/A')}, "
            f"partial_tp_hit={pos.get('take_profit_partial_hit', False)}\n"
        )

    suspended_warning = ""
    if suspended_strategies:
        suspended_warning = (
            f"\n⛔ SUSPENDED STRATEGIES (avoid these — poor empirical results): "
            + ", ".join(suspended_strategies)
        )

    prompt = f"""Market Check

{market_summary}

{technicals_summary}

### VIX Term Structure
{vix_summary}

{correlation_summary}

{regime_summary}

{sizing_summary}

### Stop-Loss & Take-Profit Levels
{stops_info if stops_info else "No open positions."}

### Your Current Portfolio
```json
{json.dumps(portfolio, indent=2)}
```

### Tradeable Instruments (you may ONLY trade these)
```json
{instrument_details}
```

### Rolling 30-Day Market Context
{rolling_context}

### Strategy Playbook (empirical patterns from trade history)
{playbook_context}
{suspended_warning}

### Recent Trade Log (last 10 entries)
{recent_trades}

### Recent Reflections (last 5 entries)
{recent_reflections}

### Latest Research Notes
{recent_research}

### Sentiment Analysis
{recent_sentiment if recent_sentiment else "No sentiment data available yet."}

### Risk Alerts
{recent_risk_alerts if recent_risk_alerts else "No recent risk alerts."}

### Economic Events Calendar
{events_calendar if events_calendar else "No events calendar available yet."}

### Asia Overnight Summary (Nikkei / Tokyo)
{handoff_summary if handoff_summary.strip() else (asia_summary if asia_summary.strip() else "No Asia data available.")}

### Europe-at-Open Summary (FTSE / London)
{europe_summary if europe_summary.strip() and not handoff_summary.strip() else ("See handoff summary above." if handoff_summary.strip() else "No Europe data available.")}

### Historical Performance Feedback
{perf_feedback}

---

INSTRUCTIONS:
1. FIRST, carefully read ALL the research notes below. They are produced by your research agent on a frequent cycle and contain the latest market analysis, alerts, and thesis. Do not skip them.
2. Review the TECHNICAL INDICATORS above. Use moving average alignment, RSI, MACD, and Bollinger Bands to assess trend and momentum for each instrument.
   - Also check OBV trend: ACCUMULATING = smart money buying; DISTRIBUTING = smart money selling. A distributing OBV on an up-trending price is a divergence warning.
3. Check the VIX TERM STRUCTURE. Inversion (VIX > VIX3M) signals acute near-term fear and often precedes sharp bounces. Normal contango = calm. Adjust your risk tolerance accordingly.
4. Note the MARKET REGIME ({regime_data.get('regime', 'UNKNOWN')}). Adjust your strategy accordingly:
   - {regime_params.get('strategy_note', 'No regime guidance available.')}
4.5. **SECTOR DIVERGENCE ANALYSIS** — Before scoring any instrument, ask: is it moving WITH the market or AGAINST it?
   - Scan the technicals for instruments that are in an uptrend (price > SMA-20, SMA-20 rising) while SPY is in a downtrend, or vice versa.
   - If you find divergence, ask WHY: Is there a supply shock? A geopolitical event? Flight-to-safety demand? Dollar movement? A divergence with an identifiable fundamental driver is a genuine opportunity signal.
   - Classify each diverging instrument as: (a) sustained divergence with driver = candidate for independent scoring; (b) single-session spike without confirmation = noise, discard; (c) divergence but no clear driver = hold, wait for confirmation.
   - Do NOT apply the regime's instrument-type bias (e.g., "avoid cyclicals") to instruments confirmed to be in sustained divergence. Score them on their individual merits.
5. Review the POSITION SIZING recommendations. These are volatility-scaled — volatile instruments get smaller positions. You may adjust within bounds but justify deviations.
5.5. Check the CORRELATION MATRIX. If you plan to hold two highly correlated instruments (r ≥ 0.85), treat them as one position for sizing purposes — you are not diversified.
6. Review the sentiment analysis for qualitative signal from news headlines.
7. Check the risk alerts — if the risk monitor flagged stop-losses, drawdowns, or volatility, address them explicitly.
8. Check the economic events calendar — avoid opening new positions ahead of high-impact events unless you have strong conviction.
9. Review the HISTORICAL PERFORMANCE FEEDBACK. Learn from past patterns — if you tend to sell winners too early or hold losers too long, adjust.
9.5. Consult the STRATEGY PLAYBOOK. If a current setup matches a documented pattern with a known win rate, use that as a prior. High-confidence patterns (≥65% win rate, 8+ trades) warrant a stronger signal. Low-sample patterns are hypotheses — treat them accordingly.
9.6. Check SUSPENDED STRATEGIES. Any strategy flagged ⛔ has empirically failed — do not execute trades that primarily rely on that approach.
10. Check STOP-LOSS & TAKE-PROFIT levels for existing positions. Trailing stops are managed automatically, but factor them into your analysis.

10. **SCORING FRAMEWORK** — Before making any trade decision, you MUST score each instrument you are considering on these dimensions:
    - **Trend score** (-2 to +2): Based on the instrument's OWN moving average alignment (SMA 20/50/200) and direction — NOT the market's trend. A sector ETF can be in a strong uptrend while SPY is falling; evaluate it on its own chart.
    - **Momentum score** (-2 to +2): Based on RSI, MACD histogram, 20-day rate of change. Strong momentum in a counter-cyclical direction (instrument rising while market falls) is a POSITIVE signal.
    - **Sentiment score** (-2 to +2): From the sentiment analysis data above
    - **Risk/reward score** (-2 to +2): Based on distance to Bollinger Bands, ATR-based targets
    - **Event risk score** (-2 to 0): Penalty for upcoming high-impact events
    - **Sector divergence score** (-1 to +2): Assess whether the instrument is moving independently of the broad market.
      - +2: Instrument in clear multi-session uptrend while SPY is in downtrend, with an identifiable fundamental driver (supply shock, geopolitical event, dollar movement, flight-to-safety)
      - +1: Instrument showing moderate independence from SPY over 2-3 sessions with plausible driver
      - 0: Instrument correlated with broad market, or insufficient data to determine
      - -1: Instrument moving opposite to market without any discernible fundamental reason (suggests mean-reversion risk, not opportunity)

    Output scores as a JSON block BEFORE your trade decision:
    ```json
    {{
      "scores": {{
        "TICKER": {{
          "trend": 0, "momentum": 0, "sentiment": 0,
          "risk_reward": 0, "event_risk": 0, "sector_divergence": 0, "composite": 0
        }}
      }}
    }}
    ```

    RULES:
    - Only BUY when composite score > {config.SCORE_BUY_THRESHOLD}
    - Only SELL (beyond automatic stops) when composite score < {config.SCORE_SELL_THRESHOLD}
    - Between {config.SCORE_SELL_THRESHOLD} and {config.SCORE_BUY_THRESHOLD}, default to HOLD
    - **REGIME BIAS OVERRIDE**: The regime's instrument-type preference (e.g., "favor defensives in downtrend") is a DEFAULT, not a veto. If an instrument scores +1 or +2 on sector divergence AND scores positively on trend and momentum on its own merits, it is eligible for a BUY regardless of its classification as "cyclical." You MUST document the divergence driver explicitly in your trade reasoning.
    - **SPIKE VS. TREND**: A single-session price spike (+5% in one day) without prior multi-session uptrend is NOT a divergence signal — it is noise. Do not buy spikes. Require at least 2-3 sessions of sustained price improvement to confirm divergence.

11. If you decide to make a trade, output it as a JSON block with the required hypothesis fields:
```json
{{
  "action": "BUY" or "SELL",
  "ticker": "SPY",
  "quantity": 1,
  "price": 512.40,
  "reasoning": "Your full reasoning here",
  "hypothesis": "What must be true for this trade to work (e.g. 'XLE will rise 3-5% over 3 sessions because crude supply constraint from OPEC cut')",
  "falsified_by": "What would prove this hypothesis wrong (e.g. 'crude drops below $75 or XLE resumes correlation with SPY decline')",
  "confidence": "High | Medium | Low",
  "horizon": "Expected timeframe (e.g. '2-4 sessions', 'intraday', '1-2 weeks')"
}}
```

The hypothesis fields are MANDATORY for all BUY trades. They are used to evaluate the trade after it closes,
and to build the strategy playbook over time. A trade without a clear hypothesis is a gamble, not a decision.

12. If you decide NOT to trade, explain why clearly. Include what you considered, what almost triggered a trade, and what conditions would change your mind.
13. You may output multiple trade JSON blocks if you want to make multiple trades.
14. After your trading decision, write a brief reflection on this analysis cycle.

### Score Dimension Weights (learned from trade history)
These weights reflect which dimensions have historically predicted outcomes for each instrument.
Apply them by multiplying each raw score by its weight before summing the composite.

{_get_weights_for_prompt()}

IMPORTANT: You must still output raw integer scores (-2 to +2) for each dimension in your JSON.
The weighted composite is computed by the system — output raw scores only.

Remember: Max position size is regime-adjusted to {regime_params.get('max_position_pct', 0.25) * 100:.0f}% currently. You have ${portfolio['cash_usd']:.2f} in cash and ${portfolio['total_value_usd']:.2f} total portfolio value."""

    # 7. Get LLM decision (with confidence-gated temperature)
    logger.info(f"Sending analysis to LLM (temp={adaptive_temp:.2f})...")
    response = call_ollama(prompt, temperature=adaptive_temp)
    logger.info(f"LLM response received ({len(response)} chars)")

    # 7.5. Extract scores from LLM response for trade attribution
    scores_by_ticker = {}
    json_pattern = r'```json\s*(.*?)\s*```'
    for match in re.findall(json_pattern, response, re.DOTALL):
        try:
            data = json.loads(match)
            if isinstance(data, dict) and "scores" in data:
                scores_by_ticker = data["scores"]
                break
        except json.JSONDecodeError:
            continue

    # 8. Parse and execute trades
    trades = parse_trades_from_response(response, portfolio)
    closed_trades = []

    if trades:
        for trade in trades:
            # Attach entry scores if available for this ticker
            ticker = trade.get("ticker", "")
            if ticker in scores_by_ticker:
                trade["entry_scores"] = scores_by_ticker[ticker]

            valid, reason = validate_trade(trade, portfolio)
            if not valid:
                logger.warning(f"Trade rejected: {reason}")
                append_to_file(
                    config.TRADE_LOG_PATH,
                    f"\n## Trade Rejected\n- **Reason:** {reason}\n"
                    f"- **Attempted:** {json.dumps(trade)}\n\n---\n",
                )
                continue

            # Bear-case adversarial debate for large BUY positions
            trade_cost = trade.get("quantity", 0) * trade.get("price", 0)
            bear_threshold = portfolio["total_value_usd"] * (config.BEAR_CASE_THRESHOLD_PCT / 100)
            bear_case_text = ""
            if trade.get("action", "").upper() == "BUY" and trade_cost >= bear_threshold:
                market_snippet = f"{regime_summary}\n{vix_summary}\n{correlation_summary[:400]}"
                _, bear_case_text = _run_bear_case_debate(trade, market_snippet)
                # Append bear case to trade reasoning so it is logged and visible
                trade["reasoning"] = (
                    trade.get("reasoning", "")
                    + f"\n\n[BEAR CASE ANALYSIS]\n{bear_case_text}"
                )
                logger.info(f"Bear case logged for {ticker} trade (${trade_cost:.2f})")

            logger.info(
                f"Executing trade: {trade['action']} "
                f"{trade['quantity']}x {trade['ticker']} @ ${trade['price']}"
            )
            portfolio, was_closed = execute_trade(trade, portfolio, technicals)
            if was_closed:
                closed_trades.append(trade)
    else:
        # No action taken — log the FULL reasoning
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"""
## No Action - {now}
- **Reasoning:** {response}

---
"""
        append_to_file(config.TRADE_LOG_PATH, log_entry)
        logger.info("No trades executed this cycle")

    # 9. Write reflections for closed positions (with hypothesis evaluation)
    for trade in closed_trades:
        hypothesis = trade.get("hypothesis", "")
        falsified_by = trade.get("falsified_by", "")
        pnl = trade.get("realized_pnl", 0)
        outcome = "WON" if pnl > 0.01 else ("LOST" if pnl < -0.01 else "NEUTRAL")

        hyp_block = ""
        if hypothesis:
            hyp_block = f"""
- Stated Hypothesis: {hypothesis}
- Falsified By condition: {falsified_by if falsified_by else "Not stated"}
- Outcome: {outcome} (${pnl:+.2f})

CRITICAL QUESTION: Was the hypothesis correct, partially correct, or wrong?
If wrong, what specifically invalidated it — did the falsification condition trigger, or did
something else happen that the hypothesis didn't account for?
"""

        reflection_prompt = f"""You just closed a trade:
- Sold {trade['quantity']}x {trade['ticker']} at ${trade['price']}
- Realized P&L: ${pnl:.2f} ({outcome})
- Original reasoning: {trade.get('reasoning', 'N/A')[:500]}
{hyp_block}
Write a reflection covering:
1. Was the hypothesis validated or falsified, and why?
2. What worked or failed in the execution (entry timing, sizing, exit)?
3. One concrete change to apply next time this setup appears.

Be specific. Reference actual price levels and indicator values where possible.
Keep it to 4-6 sentences."""

        reflection = call_ollama(reflection_prompt)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pnl = trade.get("realized_pnl", 0)
        pnl_label = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
        append_to_file(
            config.REFLECTIONS_PATH,
            f"\n## Reflection - {trade['ticker']} CLOSED ({pnl_label}) - {now}\n"
            f"{reflection}\n\n---\n",
        )
        logger.info(f"Reflection written for closed {trade['ticker']} position")

    # 10. Write a cycle reflection
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    action_summary = (
        f"Executed {len(trades)} trade(s)" if trades
        else "No trades — held positions"
    )

    reflection_prompt = f"""You just completed an hourly market analysis cycle at {now}.

Action taken: {action_summary}
Market regime: {regime_data.get('regime', 'UNKNOWN')}

Here is your full analysis from this cycle:
{response[:3000]}

Write a brief 2-3 sentence reflection on this analysis cycle for your learning log.
Focus on: What did you observe? Was there anything surprising? What will you watch for next hour?"""

    hourly_reflection = call_ollama(reflection_prompt)
    append_to_file(
        config.REFLECTIONS_PATH,
        f"\n## Market Check Reflection - {now}\n"
        f"**Action:** {action_summary}\n"
        f"**Regime:** {regime_data.get('regime', 'UNKNOWN')}\n\n"
        f"{hourly_reflection}\n\n---\n",
    )
    logger.info("Market check reflection written")

    logger.info("Market check complete")


def run_morning_report():
    """Generate the daily morning report.

    Now includes Asia overnight and Europe-at-open summaries from the
    overseas monitors, providing a full follow-the-sun context before
    the U.S. session begins.
    """
    logger.info("Generating morning report...")

    portfolio = load_portfolio()
    recent_trades = read_recent_entries(config.TRADE_LOG_PATH, 20)
    recent_reflections = read_recent_entries(config.REFLECTIONS_PATH, 10)
    recent_research = read_recent_entries(config.RESEARCH_PATH, 3)
    market_summary = get_market_summary()

    # Read overseas monitor summaries — prefer the consolidated handoff
    # summary when available, fall back to raw Asia + Europe feeds
    handoff_summary = read_recent_entries(config.HANDOFF_SUMMARY_PATH, 1)
    asia_summary = read_recent_entries(config.NIKKEI_MONITOR_PATH, 3)
    europe_summary = read_recent_entries(config.FTSE_MONITOR_PATH, 3)

    if handoff_summary.strip():
        overseas_block = f"""### Overnight Handoff Summary (consolidated Asia + Europe)
{handoff_summary}"""
    else:
        overseas_block = f"""### Asia Overnight Summary (Nikkei / Tokyo)
{asia_summary if asia_summary.strip() else "No Asia data available — monitors may not have run yet."}

### Europe-at-Open Summary (FTSE / London)
{europe_summary if europe_summary.strip() else "No Europe data available — monitors may not have run yet."}"""

    gain_loss = portfolio["total_value_usd"] - portfolio["starting_capital"]
    pct_return = (gain_loss / portfolio["starting_capital"]) * 100

    prompt = f"""Morning Report

Generate a daily trading report. Today is {datetime.now().strftime('%Y-%m-%d')}.

### Current Portfolio State
```json
{json.dumps(portfolio, indent=2)}
```

### Performance
- Starting Capital: $1,000.00
- Current Value: ${portfolio['total_value_usd']:.2f}
- Gain/Loss: ${gain_loss:+.2f}
- Return: {pct_return:+.2f}%
- All-Time High: ${portfolio['all_time_high']:.2f}
- All-Time Low: ${portfolio['all_time_low']:.2f}
- Total Trades: {portfolio['trade_count']}

{overseas_block}

### Recent Trade Log
{recent_trades}

### Recent Reflections
{recent_reflections}

### Latest Research
{recent_research}

### Current Market Conditions
{market_summary}

---

Write the full morning report with these sections:
1. Portfolio Summary (cash, total value, gain/loss, % return)
2. Open Positions (ticker, entry price, current price, quantity, unrealized P&L, rationale)
3. Asia Overnight Recap (Nikkei direction, key themes, divergence from prior U.S. close)
4. Europe-at-Open Recap (FTSE direction, key themes, Asia-to-Europe handoff)
5. Cross-Market Handoff Summary (what Asia and Europe are telling us about the U.S. day ahead, key risks and catalysts)
6. Trades Made Yesterday (summary of last 24h trades with reasoning)
7. Performance Reflection (what went well, what didn't, one thing to change today)
8. Market Outlook (your read on global conditions — Asia, Europe, U.S. — and what you're watching)
9. Research Summary (key findings from your latest research notes)

Be specific and honest. Do not omit trades or rationalize poor decisions."""

    report = call_ollama(prompt, model=config.REPORT_MODEL)

    # Save report
    today = datetime.now().strftime("%Y-%m-%d")
    report_path = f"{config.REPORTS_DIR}/{today}_report.md"
    with open(report_path, "w") as f:
        f.write(f"# Morning Report - {today}\n\n")
        f.write(report)

    logger.info(f"Morning report saved to {report_path}")
