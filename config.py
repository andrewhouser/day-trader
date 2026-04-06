"""Configuration for the day-trader agent."""
import os

# Ollama settings
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
TRADER_MODEL_NAME = os.getenv("TRADER_MODEL_NAME", "deepseek-r1:14b")  # Trading agent (complex reasoning, trade decisions)
RESEARCH_MODEL = os.getenv("RESEARCH_MODEL", "qwen3.5:latest")  # Research, summarizer, performance, rebalancer (analysis/long context)
REPORT_MODEL = os.getenv("REPORT_MODEL", "qwen2.5:7b")  # Morning report (formatting/summarization)
SENTIMENT_MODEL = os.getenv("SENTIMENT_MODEL", "llama3.1:8b")  # Sentiment agent (classification)
EVENTS_MODEL = os.getenv("EVENTS_MODEL", "qwen2.5:7b")  # Events calendar (structured generation, fast)
EXPANSION_MODEL = os.getenv("EXPANSION_MODEL", "qwen3.5:latest")  # Expansion analysis (portfolio analysis)
COMPACTION_MODEL = os.getenv("COMPACTION_MODEL", "phi3:3.8b")  # Compaction (lightweight summarization)
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.3"))
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))  # Default timeout for Ollama requests (seconds)
EVENTS_TIMEOUT = int(os.getenv("EVENTS_TIMEOUT", "600"))  # Extended timeout for events calendar (seconds)
RESEARCH_TIMEOUT = int(os.getenv("RESEARCH_TIMEOUT", "600"))  # Extended timeout for research agent (seconds)
PERFORMANCE_TIMEOUT = int(os.getenv("PERFORMANCE_TIMEOUT", "900"))  # Extended timeout for performance analyst (seconds)

# Scheduling (cron-style, all times in TIMEZONE)
# NOTE: APScheduler from_crontab uses ISO weekdays: 0=Mon … 6=Sun
# (NOT standard cron where 0=Sun). All day-of-week values below
# use the APScheduler convention.
#
# U.S. market hours: 9:30 AM – 4:00 PM ET, Mon–Fri
HOURLY_CRON = os.getenv("HOURLY_CRON", "0,30 9-16 * * 0-4")  # Every 30 min 9 AM–4 PM, Mon–Fri
MORNING_REPORT_CRON = os.getenv("MORNING_REPORT_CRON", "0 7 * * 0-4")  # 7:00 AM weekdays
RESEARCH_CRON = os.getenv("RESEARCH_CRON", "5/10 9-16 * * 0-4")  # Every 10 min offset by 5 (:05,:15,:25,...) during market hours, Mon–Fri
SENTIMENT_CRON = os.getenv("SENTIMENT_CRON", "0 8,12,16 * * 0-4")  # 8 AM, 12 PM, 4 PM weekdays
RISK_MONITOR_CRON = os.getenv("RISK_MONITOR_CRON", "*/3 9-16 * * 0-4")  # Every 3 min during market hours
REBALANCER_CRON = os.getenv("REBALANCER_CRON", "0 6 * * 0")  # 6 AM every Monday
PERFORMANCE_CRON = os.getenv("PERFORMANCE_CRON", "0 6 * * 4")  # 6 AM every Friday
EVENTS_CRON = os.getenv("EVENTS_CRON", "0 6 * * 0-4")  # 6 AM weekdays
EXPANSION_CRON = os.getenv("EXPANSION_CRON", "0 7 * * 2")  # 7 AM every Wednesday
PLAYBOOK_CRON = os.getenv("PLAYBOOK_CRON", "30 6 * * 4")  # 6:30 AM every Friday (after Performance Analysis at 6 AM)
MARKET_CONTEXT_CRON = os.getenv("MARKET_CONTEXT_CRON", "55 6 * * 0-4")  # 6:55 AM weekdays (just before market open)

# ── Overseas market monitor schedules (all times in TIMEZONE / ET) ──
# Nikkei / Tokyo Stock Exchange
#   TSE opens ~8:00 PM ET (previous day), midday break, reopens ~11:30 PM ET
#   Note: Japan does NOT observe DST. When the U.S. shifts to EDT the ET
#   offsets move by one hour. Adjust these crons or add DST-aware logic later.
#   Sun–Thu evenings in APScheduler: 6=Sun, 0=Mon, 1=Tue, 2=Wed, 3=Thu
NIKKEI_OPEN_CRON = os.getenv("NIKKEI_OPEN_CRON", "*/10 19-22 * * 6,0-3")  # Every 10 min, 7 PM–10:30 PM ET, Sun–Thu
NIKKEI_REOPEN_CRON = os.getenv("NIKKEI_REOPEN_CRON", "*/15 23 * * 6,0-3")  # Every 15 min, 11 PM ET, Sun–Thu (hour 23 portion)
NIKKEI_REOPEN_LATE_CRON = os.getenv("NIKKEI_REOPEN_LATE_CRON", "*/15 0-2 * * 0-4")  # Every 15 min, midnight–2:30 AM ET, Mon–Fri

# FTSE / London Stock Exchange
#   LSE opens ~3:00 AM ET
#   Note: UK observes DST (BST) but shifts on different dates than the U.S.
#   There are ~2 weeks/year where the ET offset is off by one hour.
FTSE_OPEN_CRON = os.getenv("FTSE_OPEN_CRON", "*/10 2-5 * * 0-4")  # Every 10 min, 2:30 AM–5:30 AM ET, Mon–Fri

# Europe Handoff Summary — synthesizes Asia + Europe into a single pre-market brief
EUROPE_HANDOFF_CRON = os.getenv("EUROPE_HANDOFF_CRON", "30 5 * * 0-4")  # 5:30 AM ET, Mon–Fri

# Overseas monitor model (defaults to RESEARCH_MODEL for analysis quality)
OVERSEAS_MODEL = os.getenv("OVERSEAS_MODEL", "")  # Empty = use RESEARCH_MODEL
OVERSEAS_TIMEOUT = int(os.getenv("OVERSEAS_TIMEOUT", "600"))
PLAYBOOK_MODEL = os.getenv("PLAYBOOK_MODEL", "")   # Empty = use RESEARCH_MODEL
PLAYBOOK_TIMEOUT = int(os.getenv("PLAYBOOK_TIMEOUT", "600"))

# Speculation agent
SPECULATION_MODEL = os.getenv("SPECULATION_MODEL", "")  # Empty = use RESEARCH_MODEL
SPECULATION_TIMEOUT = int(os.getenv("SPECULATION_TIMEOUT", "600"))
SPECULATION_CRON = os.getenv("SPECULATION_CRON", "0 10,11,13,14,15 * * 0-4")  # 10 AM, 11 AM, 1 PM, 2 PM, 3 PM weekdays

# Adversarial bear-case debate: minimum position size (% of portfolio) to trigger
BEAR_CASE_THRESHOLD_PCT = float(os.getenv("BEAR_CASE_THRESHOLD_PCT", "5.0"))
# Confidence-gated temperature thresholds
PLAYBOOK_HIGH_CONFIDENCE_WIN_RATE = float(os.getenv("PLAYBOOK_HIGH_CONFIDENCE_WIN_RATE", "0.65"))  # ≥65% win rate → low temp
PLAYBOOK_HIGH_CONFIDENCE_MIN_TRADES = int(os.getenv("PLAYBOOK_HIGH_CONFIDENCE_MIN_TRADES", "8"))   # Minimum samples required
TEMPERATURE_HIGH_CONFIDENCE = float(os.getenv("TEMPERATURE_HIGH_CONFIDENCE", "0.1"))
TEMPERATURE_NO_PATTERN = float(os.getenv("TEMPERATURE_NO_PATTERN", "0.6"))

TIMEZONE = os.getenv("TZ", "America/New_York")

# File paths
DATA_DIR = os.getenv("DATA_DIR", "/app/trader")
PORTFOLIO_PATH = os.path.join(DATA_DIR, "portfolio.json")
TRADE_LOG_PATH = os.path.join(DATA_DIR, "trade_log.md")
REFLECTIONS_PATH = os.path.join(DATA_DIR, "reflections.md")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
RESEARCH_PATH = os.path.join(DATA_DIR, "research.md")
RESEARCH_HISTORY_PATH = os.path.join(DATA_DIR, "research_history.md")
TRADE_HISTORY_PATH = os.path.join(DATA_DIR, "trade_history.md")
LESSONS_PATH = os.path.join(DATA_DIR, "lessons.md")
SENTIMENT_PATH = os.path.join(DATA_DIR, "sentiment.md")
RISK_ALERTS_PATH = os.path.join(DATA_DIR, "risk_alerts.md")
PERFORMANCE_PATH = os.path.join(DATA_DIR, "performance.md")
EVENTS_PATH = os.path.join(DATA_DIR, "events.md")
PORTFOLIO_HISTORY_PATH = os.path.join(DATA_DIR, "portfolio_history.json")
MARKET_RESEARCH_PATH = os.path.join(DATA_DIR, "market_research.json")
MARKET_BRIEF_PATH = os.path.join(DATA_DIR, "market_brief.md")
TASK_HISTORY_PATH = os.path.join(DATA_DIR, "task_history.json")
PLAYBOOK_PATH = os.path.join(DATA_DIR, "playbook.md")
MARKET_CONTEXT_PATH = os.path.join(DATA_DIR, "market_context.md")
STRATEGY_SCORES_PATH = os.path.join(DATA_DIR, "strategy_scores.json")
SPECULATION_PATH = os.path.join(DATA_DIR, "speculation.md")

# Overseas market monitor output files
NIKKEI_MONITOR_PATH = os.path.join(DATA_DIR, "nikkei_monitor.md")
FTSE_MONITOR_PATH = os.path.join(DATA_DIR, "ftse_monitor.md")
HANDOFF_SUMMARY_PATH = os.path.join(DATA_DIR, "handoff_summary.md")
OVERSEAS_SIGNALS_PATH = os.path.join(DATA_DIR, "overseas_signals.json")

# Overseas signal thresholds — minimum move % to emit a trade signal
OVERSEAS_SIGNAL_THRESHOLD_PCT = float(os.getenv("OVERSEAS_SIGNAL_THRESHOLD_PCT", "1.5"))
# Maximum age (hours) before a signal is considered stale and auto-expired
OVERSEAS_SIGNAL_MAX_AGE_HOURS = int(os.getenv("OVERSEAS_SIGNAL_MAX_AGE_HOURS", "14"))

# Market data
MARKET_DATA_SOURCE = os.getenv("MARKET_DATA_SOURCE", "yfinance")  # yfinance or alphavantage
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY", "")

# Multi-source research engine keys
FRED_API_KEY = os.getenv("FRED_API_KEY", "")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
SEC_EDGAR_CONTACT = os.getenv("SEC_EDGAR_CONTACT", "research-agent@example.com")

# Research engine settings
RESEARCH_MAX_WORKERS = int(os.getenv("RESEARCH_MAX_WORKERS", "5"))
RESEARCH_CACHE_ENABLED = os.getenv("RESEARCH_CACHE_ENABLED", "true").lower() == "true"

# Instruments in scope
INSTRUMENTS = {
    # Core broad-market ETFs
    "SPY": {"type": "ETF", "tracks": "S&P 500"},
    "QQQ": {"type": "ETF", "tracks": "NASDAQ-100"},
    "DIA": {"type": "ETF", "tracks": "DOW Jones Industrial Average"},
    # International ETFs
    "EWJ": {"type": "ETF", "tracks": "Japan (Nikkei proxy)"},
    "EWU": {"type": "ETF", "tracks": "United Kingdom (FTSE proxy)"},
    "EWG": {"type": "ETF", "tracks": "Germany (DAX proxy)"},
    # Sector ETFs
    "XLK": {"type": "ETF", "tracks": "Technology Select Sector (cyclical)"},
    "XLF": {"type": "ETF", "tracks": "Financial Select Sector (cyclical)"},
    "XLE": {"type": "ETF", "tracks": "Energy Select Sector (cyclical)"},
    "XLV": {"type": "ETF", "tracks": "Health Care Select Sector"},
    "XBI": {"type": "ETF", "tracks": "S&P Biotech (high beta)"},
    "XLI": {"type": "ETF", "tracks": "Industrial Select Sector (cyclical)"},
    "XLP": {"type": "ETF", "tracks": "Consumer Staples Select Sector (defensive)"},
    "XLU": {"type": "ETF", "tracks": "Utilities Select Sector (defensive)"},
    # Bond ETFs
    "TLT": {"type": "ETF", "tracks": "20+ Year Treasury Bond (long duration)"},
    "SHY": {"type": "ETF", "tracks": "1-3 Year Treasury Bond (short duration, safe haven)"},
    "AGG": {"type": "ETF", "tracks": "US Aggregate Bond (broad fixed income)"},
    # Commodity ETFs
    "GLD": {"type": "ETF", "tracks": "Gold (inflation hedge, safe haven)"},
    "SLV": {"type": "ETF", "tracks": "Silver (precious metal, industrial)"},
    "USO": {"type": "ETF", "tracks": "United States Oil Fund (crude oil)"},
}

# Index symbols for monitoring
INDICES = {
    "^DJI": "DOW Jones Industrial Average",
    "^IXIC": "NASDAQ Composite",
    "^GSPC": "S&P 500",
    "^N225": "Nikkei 225",
    "^FTSE": "FTSE 100",
}

# Risk management
MAX_POSITION_PCT = 0.25  # Max 25% of portfolio in a single position
MAX_RECENT_ENTRIES = 20  # Read only last N entries from logs when context is large

# Trailing stop / take-profit settings
TRAILING_STOP_ATR_MULTIPLIER = float(os.getenv("TRAILING_STOP_ATR_MULTIPLIER", "2.0"))
INITIAL_STOP_ATR_MULTIPLIER = float(os.getenv("INITIAL_STOP_ATR_MULTIPLIER", "1.5"))
TAKE_PROFIT_PARTIAL_PCT = float(os.getenv("TAKE_PROFIT_PARTIAL_PCT", "5.0"))  # Sell 50% at this gain %
TAKE_PROFIT_FULL_PCT = float(os.getenv("TAKE_PROFIT_FULL_PCT", "8.0"))  # Sell remaining at this gain %

# Position sizing (volatility-scaled)
RISK_BUDGET_PCT = float(os.getenv("RISK_BUDGET_PCT", "2.0"))  # % of portfolio risked per trade

# Market regime parameters
REGIME_PARAMS = {
    "STRONG_UPTREND": {
        "max_position_pct": 0.25,
        "stop_atr_multiplier": 2.0,
        "regime_multiplier": 1.0,
        "strategy_note": "Strong uptrend — full position sizes, favor buying dips in cyclicals (XLK, XLF, XLE)",
    },
    "UPTREND": {
        "max_position_pct": 0.25,
        "stop_atr_multiplier": 2.0,
        "regime_multiplier": 1.0,
        "strategy_note": "Uptrend — full position sizes, favor buying dips",
    },
    "SIDEWAYS": {
        "max_position_pct": 0.15,
        "stop_atr_multiplier": 2.0,
        "regime_multiplier": 0.75,
        "strategy_note": "Sideways — reduce max position to 15%, favor mean reversion",
    },
    "DOWNTREND": {
        "max_position_pct": 0.12,
        "stop_atr_multiplier": 1.5,
        "regime_multiplier": 0.7,
        "strategy_note": (
            "Downtrend — reduce max position to 10%, favor cash and defensives (XLU, XLP, TLT, SHY, GLD). "
            "REGIME BIAS IS A DEFAULT, NOT AN ABSOLUTE RULE: before dismissing any instrument, check whether "
            "it is moving independently of SPY. Energy (XLE, USO), gold (GLD), and commodities often trade on "
            "supply/demand or geopolitical factors uncorrelated with equities. If an instrument has been trending "
            "upward for 3+ sessions while SPY is falling, that is a divergence signal — score it on its own "
            "technicals and fundamental driver rather than applying the cyclical penalty. Require: (a) multi-session "
            "uptrend confirmation, (b) an identifiable fundamental driver, (c) position sized at the lower end of "
            "the 10% cap given elevated market risk."
        ),
    },
    "STRONG_DOWNTREND": {
        "max_position_pct": 0.10,
        "stop_atr_multiplier": 1.5,
        "regime_multiplier": 0.5,
        "strategy_note": (
            "Strong downtrend — reduce max position to 10%, favor cash, tighten stops, defensives only "
            "(XLU, XLP, TLT, SHY, GLD). Divergence exceptions require very high conviction: 5+ sessions of "
            "counter-trend movement with a clear fundamental catalyst (e.g., OPEC supply cut, geopolitical "
            "supply disruption) and confirmation that the instrument is not merely exhibiting a dead-cat bounce. "
            "Single-day spikes in strong downtrends are almost always noise — require multi-day follow-through."
        ),
    },
    "HIGH_VOLATILITY": {
        "max_position_pct": 0.10,
        "stop_atr_multiplier": 2.5,
        "regime_multiplier": 0.5,
        "strategy_note": "High volatility — reduce max position to 10%, widen stops to 2.5x ATR, favor safe havens (GLD, TLT, SHY)",
    },
}

# Scoring framework thresholds
SCORE_BUY_THRESHOLD = int(os.getenv("SCORE_BUY_THRESHOLD", "3"))
SCORE_SELL_THRESHOLD = int(os.getenv("SCORE_SELL_THRESHOLD", "-3"))

# Dynamic buy threshold: when cash exceeds HIGH_CASH_PCT, use a lower buy threshold
# to reduce cash drag and encourage cautious deployment
SCORE_BUY_THRESHOLD_HIGH_CASH = int(os.getenv("SCORE_BUY_THRESHOLD_HIGH_CASH", "2"))
HIGH_CASH_PCT = float(os.getenv("HIGH_CASH_PCT", "70.0"))  # % cash to trigger lower threshold

# Speculative trade threshold: speculation-backed trades with reward/risk >= 2.0
# can use a lower composite score threshold with a capped position size
SCORE_BUY_THRESHOLD_SPECULATIVE = int(os.getenv("SCORE_BUY_THRESHOLD_SPECULATIVE", "2"))
SPECULATION_MAX_POSITION_PCT = float(os.getenv("SPECULATION_MAX_POSITION_PCT", "0.05"))  # 5% cap

# Momentum pulse: lightweight intraday momentum scanner
MOMENTUM_PULSE_CRON = os.getenv("MOMENTUM_PULSE_CRON", "*/10 10-15 * * 0-4")  # Every 10 min, 10 AM–3 PM weekdays
MOMENTUM_PULSE_PATH = os.path.join(DATA_DIR, "momentum_pulse.json")
MOMENTUM_REVERSAL_RECOVERY_PCT = float(os.getenv("MOMENTUM_REVERSAL_RECOVERY_PCT", "60.0"))  # % recovery from session low to flag reversal

# Compaction settings
COMPACTION_CRON = os.getenv("COMPACTION_CRON", "0 5 * * 1-5")  # 5:00 AM weekdays (before morning report)
RESEARCH_KEEP_ENTRIES = int(os.getenv("RESEARCH_KEEP_ENTRIES", "3"))  # Keep last N research entries after compaction
TRADE_LOG_RETENTION_DAYS = int(os.getenv("TRADE_LOG_RETENTION_DAYS", "30"))  # Keep raw trades for N days
REFLECTIONS_RETENTION_DAYS = int(os.getenv("REFLECTIONS_RETENTION_DAYS", "14"))  # Keep raw reflections for N days

# Research-triggered trading thresholds
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "3.0"))       # Trigger trade review if position drops this %
OPPORTUNITY_PCT = float(os.getenv("OPPORTUNITY_PCT", "2.0"))    # Trigger trade review if instrument surges this %

# Risk monitor thresholds
RISK_VOLATILITY_THRESHOLD = float(os.getenv("RISK_VOLATILITY_THRESHOLD", "2.5"))  # % intraday swing to flag
RISK_CORRELATION_THRESHOLD = float(os.getenv("RISK_CORRELATION_THRESHOLD", "0.85"))  # Correlation threshold for concentration warning
RISK_MAX_DRAWDOWN_PCT = float(os.getenv("RISK_MAX_DRAWDOWN_PCT", "5.0"))  # Portfolio drawdown % to trigger alert

# Rebalancer settings
REBALANCER_TARGET_CASH_PCT = float(os.getenv("REBALANCER_TARGET_CASH_PCT", "20.0"))  # Target cash allocation %
REBALANCER_DRIFT_THRESHOLD = float(os.getenv("REBALANCER_DRIFT_THRESHOLD", "10.0"))  # % drift before suggesting rebalance

SYSTEM_PROMPT = """You are a simulated day-trading agent. You do not trade real money. You manage a paper portfolio that starts with $1,000.00 USD. You treat every trade as though it were real.

Your job is to:
1. Monitor the DOW Jones Industrial Average, NASDAQ Composite, S&P 500, and at least two international indices (such as the Nikkei 225, FTSE 100, DAX, or Hang Seng) every hour during market hours.
2. Analyze current conditions, trends, news, and momentum.
3. Make buy or sell decisions based on your analysis using a moderate, balanced risk profile. You do not chase high-risk plays. You look for asymmetric opportunities where the upside is reasonable and the downside is managed.
4. Record every trade you make, including your reasoning at the time.
5. Reflect on past trades to identify what worked, what did not, and why. Use these reflections to improve future decisions.
6. Generate a morning report every day at 7:00 AM local time summarizing your positions, trades, reasoning, and current portfolio balance.

You are allowed to hold cash. You do not have to be fully invested at all times.

You track your own state in a file called portfolio.json. You append to a trade log called trade_log.md. You write your morning report to a file called reports/YYYY-MM-DD_report.md.

You think out loud before making decisions. Show your chain of reasoning before committing to a trade.

INSTRUMENT SCOPE:
- You start with a core set of ETFs: SPY, QQQ, DIA, EWJ, EWU, EWG.
- Sector ETFs: XLK (tech), XLF (financials), XLE (energy), XLV (healthcare), XBI (biotech), XLI (industrials), XLP (consumer staples), XLU (utilities).
- Bond ETFs: TLT (long-term treasury), SHY (short-term treasury), AGG (aggregate bond).
- Commodity ETFs: GLD (gold), SLV (silver), USO (oil).
- SECTOR ROTATION: In downtrends, favor defensive sectors (XLU, XLP) and bonds (TLT, SHY). In uptrends, favor cyclical sectors (XLK, XLF, XLE). In high volatility, favor safe havens (GLD, TLT, SHY).
- SECTOR DIVERGENCE: Regime rules set a default bias — they are NOT a blanket veto. Energy (XLE, USO), gold (GLD), and silver (SLV) frequently move on supply, demand, or geopolitical drivers that are uncorrelated with — or even inversely correlated to — equity indices. If a sector ETF is trending strongly UPWARD while SPY is trending DOWNWARD over multiple sessions, it is behaving counter-cyclically in that context and deserves independent evaluation. Do NOT penalize it simply for being labeled "cyclical." Evaluate: (1) Is the instrument technically in its own uptrend (price above SMA-20, SMA-20 rising)? (2) Is there a clear fundamental driver (oil supply shock, flight-to-safety, dollar weakness)? (3) Is the divergence sustained across 3+ sessions or just a single-day spike? A single-day spike is noise. Sustained multi-session divergence with a confirmed driver is a genuine asymmetric opportunity and should be scored accordingly.
- Additional instruments (individual stocks, REITs, etc.)
  may be added to your tradeable set over time through the expansion proposal process.
- The expansion agent periodically suggests new instruments for portfolio diversification.
- These proposals require explicit user approval before you can trade them.
- Once approved, they appear in your instruments list and you may trade them normally.
- You may ONLY trade instruments that appear in your current instruments list.
  Do not attempt to trade instruments that have not been approved.

RISK RULES:
- Never put more than the regime-adjusted max % of total portfolio value into a single position (default 25%, reduced in downtrends/volatility).
- Position sizes should be volatility-scaled: volatile instruments get smaller positions.
- Trailing stops and take-profit targets are managed automatically — respect them.
- Do not be fully invested unless conditions are clearly favorable.
- Never execute a trade without logging your full reasoning. If reasoning is thin, hold.
- Never revise past trade logs. Acknowledge losses honestly.

LEARNING LOOP:
- Before each analysis, re-read your most recent reflections to carry forward lessons.
- After every closed trade, write a reflection assessing the outcome."""
