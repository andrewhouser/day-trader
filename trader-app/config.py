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

# Scheduling (cron-style, all times in TIMEZONE)
# U.S. market hours: 9:30 AM – 4:00 PM ET, Mon–Fri
HOURLY_CRON = os.getenv("HOURLY_CRON", "0,30 9-16 * * 1-5")  # Every 30 min 9 AM–4 PM, Mon–Fri
MORNING_REPORT_CRON = os.getenv("MORNING_REPORT_CRON", "0 7 * * 1-5")  # 7:00 AM weekdays
RESEARCH_CRON = os.getenv("RESEARCH_CRON", "5/10 9-16 * * 1-5")  # Every 10 min offset by 5 (:05,:15,:25,...) during market hours, Mon–Fri
SENTIMENT_CRON = os.getenv("SENTIMENT_CRON", "0 8,12,16 * * 1-5")  # 8 AM, 12 PM, 4 PM weekdays
RISK_MONITOR_CRON = os.getenv("RISK_MONITOR_CRON", "*/3 9-16 * * 1-5")  # Every 3 min during market hours
REBALANCER_CRON = os.getenv("REBALANCER_CRON", "0 6 * * 1")  # 6 AM every Monday
PERFORMANCE_CRON = os.getenv("PERFORMANCE_CRON", "0 6 * * 5")  # 6 AM every Friday
EVENTS_CRON = os.getenv("EVENTS_CRON", "0 6 * * 1-5")  # 6 AM weekdays
EXPANSION_CRON = os.getenv("EXPANSION_CRON", "0 7 * * 3")  # 7 AM every Wednesday
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
        "max_position_pct": 0.10,
        "stop_atr_multiplier": 1.5,
        "regime_multiplier": 0.5,
        "strategy_note": "Downtrend — reduce max position to 10%, favor cash and defensives (XLU, XLP, TLT, SHY, GLD)",
    },
    "STRONG_DOWNTREND": {
        "max_position_pct": 0.10,
        "stop_atr_multiplier": 1.5,
        "regime_multiplier": 0.5,
        "strategy_note": "Strong downtrend — reduce max position to 10%, favor cash, tighten stops, defensives only (XLU, XLP, TLT, SHY, GLD)",
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
