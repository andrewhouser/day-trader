# Day Trader Agent

A fully autonomous, simulated day-trading agent that monitors global markets, executes paper trades, and learns from its own performance over time. It starts with $1,000 USD of fake money and runs entirely inside Docker.

No real money is involved. All trades are simulated and tracked on disk.

![Paper Day Trader](images/PaperDayTrader.png)

## Architecture

The project is split into two services that run together via Docker Compose:

```
┌──────────────────────────────────────────────────────────────┐
│  trader (Python / FastAPI)                                   │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  APScheduler (10 scheduled jobs)                        │ │
│  │                                                         │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │ │
│  │  │ Research  │ │ Trader   │ │Sentiment │ │   Risk    │  │ │
│  │  │ (10 min) │ │ (30 min) │ │  (3x/d)  │ │ (3 min)   │  │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └───────────┘  │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │ │
│  │  │ Report   │ │Rebalancer│ │Performanc│ │  Events   │  │ │
│  │  │ (7 AM)   │ │ (Mon)    │ │  (Fri)   │ │  (6 AM)   │  │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └───────────┘  │ │
│  │  ┌──────────┐ ┌──────────┐                              │ │
│  │  │Compaction│ │Expansion │                              │ │
│  │  │ (5 AM)   │ │ (Wed)    │                              │ │
│  │  └──────────┘ └──────────┘                              │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────┐  ┌───────────────┐  ┌────────────────────┐  │
│  │ Agent Core │  │  REST API     │  │ trader/ (persist)  │  │
│  │ Ollama LLM │──│  FastAPI :8000│──│ portfolio, logs,   │  │
│  └────────────┘  └───────────────┘  │ reports, alerts     │  │
│                          ▲          └────────────────────┘  │
└──────────────────────────┼───────────────────────────────────┘
                           │
┌──────────────────────────┼───────────────────────────────────┐
│  web (Next.js)           │                                   │
│  ┌───────────────────────┴───────────────────────────────┐   │
│  │  Dashboard UI :3000  (11 tabs)                        │   │
│  │  Proxies /api/* → trader:8000                         │   │
│  └───────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### Backend (`trader` service)

- **Language:** Python 3.12
- **Framework:** FastAPI + Uvicorn
- **Scheduler:** APScheduler (background, runs inside the API process)
- **LLM:** Ollama (self-hosted, configurable models)
- **Market data:** yfinance (historical + fallback prices), Finnhub `/quote` real-time quotes (ETFs, when `FINNHUB_API_KEY` is set)
- **Technical analysis:** pandas-ta (SMA, EMA, RSI, MACD, Bollinger Bands, ATR)

### Frontend (`web` service)

- **Framework:** Next.js 14 (React 18, App Router)
- **Styling:** Custom CSS (dark theme, no external UI library)
- **Rendering:** Client-side components with auto-refresh polling

## Agents

The system runs ten scheduled agents, each with a distinct responsibility:

### Core Trading Loop

| Agent | Schedule | Model | Description |
|-------|----------|-------|-------------|
| Market Research | Every 10 min (9 AM–4 PM) | `qwen3.5:latest` | Gathers market data from 7 sources, produces structured research notes, checks stop-loss/opportunity alerts. Triggers the trader if alerts fire. |
| Market Check | Every 30 min (9 AM–4 PM) | `deepseek-r1:14b` | Full trading cycle — reads research, sentiment, risk alerts, events, technical indicators, regime, and scoring framework, then decides to buy/sell/hold, executes trades, writes reflections. |
| Morning Report | 7:00 AM weekdays | `qwen2.5:7b` | Generates a daily summary report with portfolio state, trades, performance, and outlook. |

### Intelligence Agents

| Agent | Schedule | Model | Description |
|-------|----------|-------|-------------|
| Sentiment Analysis | 8 AM, 12 PM, 4 PM weekdays | `llama3.1:8b` | Scrapes news headlines via yfinance, scores each instrument as bullish/neutral/bearish with confidence levels. Writes `sentiment.md` consumed by the trader. |
| Events Calendar | 6:00 AM weekdays | `qwen2.5:7b` | Fetches upcoming economic events (FOMC, jobs, CPI, earnings) and writes `events.md`. The trader uses this to avoid opening positions ahead of high-impact events. |

### Risk & Portfolio Management

| Agent | Schedule | Model | Description |
|-------|----------|-------|-------------|
| Risk Monitor | Every 3 min (9 AM–4 PM) | None (rule-based) | Watches for trailing stop breaches, take-profit targets, portfolio drawdown, volatility spikes, and position correlation. Automatically executes trailing stop and take-profit sells. Wakes the trader on critical alerts. |
| Portfolio Rebalancer | 6:00 AM Mondays | `qwen3.5:latest` | Analyzes allocation drift, concentration risk, and cash drag. Suggests and executes rebalancing trades when positions drift beyond thresholds. |

### Expansion & Analytics

| Agent | Schedule | Model | Description |
|-------|----------|-------|-------------|
| Expansion Analysis | 7:00 AM Wednesdays | `qwen3.5:latest` | Evaluates potential new instruments for portfolio diversification. Generates proposals that require user approval before trading. |
| Performance Analyst | 6:00 AM Fridays | `qwen3.5:latest` | Computes win rate, profit factor, per-instrument breakdown, max drawdown, holding period analysis, and pattern detection. Generates quantitative feedback fed into the trading prompt. |
| Memory Compaction | 5:00 AM weekdays | `phi3:3.8b` | Summarizes old entries to prevent unbounded file growth. Archives research, trades, and reflections into compressed history files. |

### Agent Data Flow

```
Events Calendar ──→ ┐
Sentiment Agent ──→ ├──→ Trader Agent ──→ Trade Log / Portfolio
Research Agent  ──→ ├──→     ↑
Risk Monitor    ──→ ┘       │
Technical Indicators ──→    │
Market Regime ──→           │
Position Sizing ──→         │
Performance Feedback ──→    │
                            │
Reflections ←───────────────┘
     │
     ↓
Performance Analyst ──→ Performance Reports ──→ Feedback Loop
Compaction Agent    ──→ Archived History
Rebalancer          ──→ Rebalancing Trades
Expansion Agent     ──→ Instrument Proposals ──→ User Approval
```

All schedules are configurable via environment variables using cron syntax.

## LLM Models

The agent uses three separate models for different tasks, allowing you to balance quality vs. speed:

| Role | Default Model | Used By |
|------|--------------|---------|
| Trader | `deepseek-r1:14b` | Market check (trading decisions) |
| Research / Analysis | `qwen3.5:latest` | Research, rebalancer, performance, expansion |
| Intelligence | `llama3.1:8b` / `qwen2.5:7b` | Sentiment (`llama3.1:8b`), events (`qwen2.5:7b`), morning report (`qwen2.5:7b`) |
| Summarization | `phi3:3.8b` | Memory compaction |

The risk monitor is purely rule-based and does not call the LLM.

## Technical Analysis

The agent computes the following technical indicators for every tradeable instrument using pandas-ta (with manual pandas fallback):

| Indicator | Parameters | Usage |
|-----------|-----------|-------|
| SMA | 20, 50, 200-period | Trend direction, support/resistance, golden/death cross detection |
| EMA | 12, 26-period | Short-term trend, MACD components |
| RSI | 14-period | Overbought/oversold (>70 / <30) |
| MACD | 12, 26, 9 | Momentum with signal line and histogram |
| Bollinger Bands | 20-period, 2 std dev | Volatility envelope, mean reversion signals |
| ATR | 14-period | Volatility measure, used for stop-loss and position sizing |
| Volume Ratio | Current / 20-day avg | Unusual volume detection |
| Rate of Change | 20-day | Momentum confirmation |

Indicators are fetched from 1 year of daily history via yfinance to ensure enough data for SMA 200.

## Market Regime Detection

The system classifies the current market into one of six regimes, stored in `regime.json`:

| Regime | Conditions | Trading Adjustments |
|--------|-----------|-------------------|
| STRONG_UPTREND | SPY above SMA 50 & 200, golden cross, ROC > 3% | Full position sizes (25%), favor cyclicals (XLK, XLF, XLE) |
| UPTREND | SPY above SMA 50 & 200, positive ROC | Full position sizes, favor buying dips |
| SIDEWAYS | Mixed signals | Reduce max position to 15%, favor mean reversion |
| DOWNTREND | SPY below SMA 50 & 200, negative ROC | Reduce max position to 10%, favor cash and defensives (XLU, XLP, TLT, SHY, GLD) |
| STRONG_DOWNTREND | SPY below SMA 50 & 200, death cross, ROC < -3% | Reduce max position to 10%, tighten stops |
| HIGH_VOLATILITY | VIX > 30 | Reduce max position to 10%, widen stops to 2.5x ATR, favor safe havens |

Regime detection uses: SPY price vs SMA 50/200, golden/death cross, RSI, VIX level, and 20-day rate of change.

## Risk Management

### Rule-Based Controls
- Regime-adjusted max position size (25% in uptrends, 10–15% in downtrends/volatility)
- Absolute ceiling of 25% of portfolio in any single position
- Configurable stop-loss threshold (default: 3% drop from entry)
- Configurable opportunity threshold (default: 2% intraday surge)
- Volatility alert threshold (default: 2.5% intraday range)
- Portfolio drawdown alert (default: 5% from all-time high)
- Correlation detection when all positions move in the same direction

### Trailing Stops & Take-Profit (Automatic)
- **Initial stop-loss:** Entry price minus 1.5× ATR, set when a position is opened
- **Trailing stop:** Highest price since entry minus 2× ATR (regime-adjusted), ratchets up only
- **Partial take-profit:** Automatically sells 50% of a position when up 5% from entry
- **Full take-profit:** Automatically sells the remaining position when up 8% from entry
- Stop and target levels are stored in `portfolio.json` alongside each position
- The risk monitor checks and executes these every 3 minutes during market hours

### Volatility-Scaled Position Sizing
- Position size = `(risk_budget / ATR)` where risk budget = 2% of portfolio value per trade
- Volatile instruments automatically get smaller positions, stable instruments get larger ones
- A regime multiplier scales the risk budget (1.0× in uptrends, 0.5× in downtrends)
- Capped at the regime-adjusted max position percentage
- Recommended sizes are included in the LLM prompt; the LLM can adjust within bounds but must justify deviations

### Structured Scoring Framework
Before any trade, the LLM must score each instrument on five dimensions (-2 to +2 each):

| Dimension | Signal Sources |
|-----------|---------------|
| Trend | Moving average alignment (SMA 20/50/200), direction |
| Momentum | RSI, MACD histogram, 20-day rate of change |
| Sentiment | News headline sentiment from the sentiment agent |
| Risk/Reward | Distance to Bollinger Bands, ATR-based targets |
| Event Risk | Penalty (-2 to 0) for upcoming high-impact events |

- **BUY** only when composite score > +3
- **SELL** (beyond automatic stops) only when composite score < -3
- **HOLD** when score is between -3 and +3

Thresholds are configurable via `SCORE_BUY_THRESHOLD` and `SCORE_SELL_THRESHOLD`.

### Quantitative Feedback Loop
The performance analyst generates per-trade stats fed back into the trading prompt:
- Win rate, average win/loss %, profit factor
- Average holding period for wins vs losses
- Best and worst trades, last 5 closed trades with outcomes
- Pattern detection (e.g., "You tend to sell winners too early and hold losers too long")
- Closed trade reflections compare predicted outcome vs actual outcome

## Tradeable Instruments

The agent trades a diversified universe of 20 ETFs across equities, sectors, bonds, and commodities:

### Core Broad-Market ETFs

| Ticker | Type | Tracks |
|--------|------|--------|
| SPY | ETF | S&P 500 |
| QQQ | ETF | NASDAQ-100 |
| DIA | ETF | DOW Jones Industrial Average |

### International ETFs

| Ticker | Type | Tracks |
|--------|------|--------|
| EWJ | ETF | Japan (Nikkei proxy) |
| EWU | ETF | United Kingdom (FTSE proxy) |
| EWG | ETF | Germany (DAX proxy) |

### Sector ETFs

| Ticker | Type | Tracks | Category |
|--------|------|--------|----------|
| XLK | ETF | Technology Select Sector | Cyclical |
| XLF | ETF | Financial Select Sector | Cyclical |
| XLE | ETF | Energy Select Sector | Cyclical |
| XLV | ETF | Health Care Select Sector | — |
| XBI | ETF | S&P Biotech | High Beta |
| XLI | ETF | Industrial Select Sector | Cyclical |
| XLP | ETF | Consumer Staples Select Sector | Defensive |
| XLU | ETF | Utilities Select Sector | Defensive |

### Bond ETFs

| Ticker | Type | Tracks |
|--------|------|--------|
| TLT | ETF | 20+ Year Treasury Bond (long duration) |
| SHY | ETF | 1-3 Year Treasury Bond (short duration, safe haven) |
| AGG | ETF | US Aggregate Bond (broad fixed income) |

### Commodity ETFs

| Ticker | Type | Tracks |
|--------|------|--------|
| GLD | ETF | Gold (inflation hedge, safe haven) |
| SLV | ETF | Silver (precious metal, industrial) |
| USO | ETF | United States Oil Fund (crude oil) |

**Sector rotation strategy:** In downtrends, the agent favors defensive sectors (XLU, XLP) and bonds (TLT, SHY). In uptrends, it favors cyclical sectors (XLK, XLF, XLE). In high volatility, it favors safe havens (GLD, TLT, SHY).

Additional instruments can be added through the expansion proposal process (the expansion agent suggests, user approves).

Monitored indices: DOW Jones (^DJI), NASDAQ Composite (^IXIC), S&P 500 (^GSPC), Nikkei 225 (^N225), FTSE 100 (^FTSE).

## Data Files

All persistent state lives in the `trader/` directory, which is volume-mounted from the host:

| File | Purpose |
|------|---------|
| `portfolio.json` | Current portfolio state (cash, positions, totals, trailing stops, take-profit levels) |
| `regime.json` | Current market regime classification and parameters |
| `trade_log.md` | Append-only log of every trade and hold decision |
| `reflections.md` | Agent self-assessments after closed trades and hourly cycles |
| `research.md` | Rolling research notes from the research agent |
| `sentiment.md` | News sentiment scores per instrument |
| `risk_alerts.md` | Risk monitor alert history (including auto-executed trailing stops and take-profits) |
| `performance.md` | Weekly quantitative performance reports |
| `events.md` | Rolling economic events calendar (overwritten daily) |
| `market_research.json` | Machine-readable multi-source research report |
| `market_brief.md` | Human-readable market research brief |
| `expansion_proposals.json` | Pending/approved/rejected expansion proposals |
| `reports/YYYY-MM-DD_report.md` | Daily morning reports |
| `reports/YYYY-MM-DD_research.md` | Daily research snapshots |
| `reports/YYYY-MM-DD_rebalance.md` | Weekly rebalance reports |
| `reports/YYYY-MM-DD_performance.md` | Weekly performance reports |
| `reports/YYYY-MM-DD_events.md` | Daily events calendar snapshots |
| `research_history.md` | Compacted daily research digests (created by compaction) |
| `trade_history.md` | Compacted monthly trade roll-ups (created by compaction) |
| `lessons.md` | Distilled trading lessons extracted from reflections (created by compaction) |

### Position Schema in portfolio.json

Each position now includes stop-loss and take-profit tracking:

```json
{
  "ticker": "SPY",
  "instrument_type": "ETF",
  "quantity": 2,
  "entry_price": 512.40,
  "entry_date": "2026-04-03T10:00:00",
  "current_price": 514.10,
  "unrealized_pnl": 3.40,
  "notes": "Entered on momentum following strong open.",
  "initial_stop": 498.20,
  "trailing_stop": 502.50,
  "highest_since_entry": 516.80,
  "take_profit_partial_hit": false
}
```

## Memory Compaction

To prevent unbounded file growth, a compaction agent runs daily at 5 AM and:

1. **Research:** Summarizes old research entries into daily digests in `research_history.md`, keeps only the last N entries in `research.md`
2. **Trade log:** Rolls up entries older than the retention period into monthly summaries in `trade_history.md`
3. **Reflections:** Distills old reflections into durable lessons in `lessons.md`, deduplicating against existing lessons

## Getting Started

### Prerequisites

- Docker and Docker Compose
- An Ollama instance with the required models pulled:
  ```bash
  ollama pull deepseek-r1:14b
  ollama pull qwen3.5:latest
  ollama pull qwen2.5:7b
  ollama pull llama3.1:8b
  ollama pull phi3:3.8b
  ```

### Configuration

Copy the example environment file and configure your Ollama URL and optional API keys:

```bash
cd trader-app
cp .env.example .env
# Edit .env with your Ollama host URL and any API keys
```

All configuration is done via environment variables in `docker-compose.yml` (which reads from `.env`):

```yaml
environment:
  - OLLAMA_BASE_URL=${OLLAMA_BASE_URL:-http://host.docker.internal:11434}  # Your Ollama host
  - TRADER_MODEL_NAME=deepseek-r1:14b
  - RESEARCH_MODEL=qwen3.5:latest
  - REPORT_MODEL=qwen2.5:7b
  - SENTIMENT_MODEL=llama3.1:8b
  - EVENTS_MODEL=qwen2.5:7b
  - EXPANSION_MODEL=qwen3.5:latest
  - COMPACTION_MODEL=phi3:3.8b
  - TEMPERATURE=0.3
  # Core trading loop
  - HOURLY_CRON=0,30 9-16 * * 1-5       # Every 30 min during market hours
  - RESEARCH_CRON=5/10 9-16 * * 1-5      # Every 10 min offset by 5
  - MORNING_REPORT_CRON=0 7 * * 1-5      # 7 AM weekdays
  # Intelligence agents
  - SENTIMENT_CRON=0 8,12,16 * * 1-5     # 3x daily
  - EVENTS_CRON=0 6 * * 1-5              # 6 AM weekdays
  # Risk & portfolio
  - RISK_MONITOR_CRON=*/3 9-16 * * 1-5   # Every 3 min during market hours
  - REBALANCER_CRON=0 6 * * 1            # 6 AM Mondays
  # Analytics & maintenance
  - PERFORMANCE_CRON=0 6 * * 5           # 6 AM Fridays
  - COMPACTION_CRON=0 5 * * 1-5          # 5 AM weekdays
  # Risk thresholds
  - STOP_LOSS_PCT=3.0
  - OPPORTUNITY_PCT=2.0
  - TRAILING_STOP_ATR_MULTIPLIER=2.0     # Trailing stop = highest - N×ATR
  - INITIAL_STOP_ATR_MULTIPLIER=1.5      # Initial stop = entry - N×ATR
  - TAKE_PROFIT_PARTIAL_PCT=5.0          # Sell 50% at this gain %
  - TAKE_PROFIT_FULL_PCT=8.0             # Sell remaining at this gain %
  - RISK_BUDGET_PCT=2.0                  # % of portfolio risked per trade
  # Scoring thresholds
  - SCORE_BUY_THRESHOLD=3               # Composite score needed to BUY
  - SCORE_SELL_THRESHOLD=-3              # Composite score needed to SELL
  - TZ=America/New_York
```

### Running

```bash
cd trader-app
docker compose up -d
```

- Backend API: http://localhost:8000
- Web dashboard: http://localhost:3000

### Running Individual Tasks

The entrypoint supports running one-off tasks:

```bash
# Core trading
docker compose run --rm trader hourly
docker compose run --rm trader research
docker compose run --rm trader report

# Intelligence
docker compose run --rm trader sentiment
docker compose run --rm trader events

# Risk & portfolio
docker compose run --rm trader risk
docker compose run --rm trader rebalance

# Analytics & maintenance
docker compose run --rm trader performance
docker compose run --rm trader compact

# Expansion
docker compose run --rm trader expansion

# Standalone scheduler (no API)
docker compose run --rm trader scheduler
```

## API Endpoints

All endpoints are prefixed with `/api`.

### Portfolio & Market

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/portfolio` | Current portfolio state (includes trailing stops and take-profit levels) |
| GET | `/api/portfolio/history?days=30` | Portfolio value history |
| GET | `/api/market/indices` | Live index levels |
| GET | `/api/market/instruments` | Live instrument prices |
| GET | `/api/market/technicals` | Technical indicators for all instruments (SMA, EMA, RSI, MACD, BB, ATR, volume ratio, ROC) |
| GET | `/api/market/regime` | Current market regime classification and parameters |
| GET | `/api/market/ticker/{ticker}/history?days=30` | Price history for a single ticker |
| GET | `/api/market/news` | Market news headlines from yfinance |

### Logs & Reports

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/trades?limit=50` | Parsed trade log entries |
| GET | `/api/reflections?limit=20` | Agent reflections |
| GET | `/api/research?limit=20` | Research notes |
| GET | `/api/reports` | List all morning reports |
| GET | `/api/reports/{filename}` | Get a specific report's content |

### Intelligence

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/sentiment?limit=10` | Sentiment analysis entries |
| GET | `/api/events` | Current economic events calendar |

### Risk & Performance

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/risk-alerts?limit=20` | Risk monitor alert history (includes auto-executed stops and take-profits) |
| GET | `/api/performance?limit=5` | Performance analysis reports |
| GET | `/api/score-weights` | Adaptive per-instrument scoring dimension weights |
| GET | `/api/stress-test` | Portfolio stress test results (cached 5 min) |

### Multi-Source Research

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/research/report` | Latest machine-readable research report (JSON) |
| GET | `/api/research/brief` | Latest human-readable market brief |
| GET | `/api/research/narratives` | Current narrative clusters |
| GET | `/api/research/sources` | Source catalog with trust metadata |
| GET | `/api/research/cache/stats` | Research cache statistics |
| POST | `/api/research/cache/clear` | Clear the research cache |

### Expansion Proposals

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/expansion/proposals` | List expansion proposals (optional `?status=` filter) |
| GET | `/api/expansion/proposals/{id}` | Get a single proposal |
| POST | `/api/expansion/proposals/{id}/approve` | Approve a proposal |
| POST | `/api/expansion/proposals/{id}/reject` | Reject a proposal |
| GET | `/api/expansion/instruments` | All currently tradeable instruments |

### Tasks

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/tasks` | Status of all scheduled tasks |
| GET | `/api/tasks/history?limit=50` | Task execution history |
| POST | `/api/tasks/{task_id}/run` | Manually trigger a task |
| POST | `/api/tasks/{task_id}/stop` | Request to stop a running task |
| PUT | `/api/tasks/{task_id}/schedule` | Update a task's cron schedule |

Task IDs: `research`, `hourly_check`, `morning_report`, `compaction`, `sentiment`, `risk_monitor`, `rebalancer`, `performance`, `events`, `expansion`

### Chat

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat` | Send a message to the trading agent with full portfolio context |

### System

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/config` | Current agent configuration |
| GET | `/api/compaction/status` | File sizes and entry counts |
| GET | `/api/health` | Health check |

## Web Dashboard

The dashboard at http://localhost:3000 provides the following views:

- **Dashboard** — Portfolio value, cash, return %, market regime badge, open positions (clickable with price history chart modal), scheduled tasks grouped by category, index tracker bar (auto-refreshes every 30s)
- **Trades** — Full trade log with expandable reasoning for each entry
- **Technicals** — Technical indicators table for all instruments (SMA, RSI, MACD, ATR, Bollinger Bands, volume ratio, ROC) with tooltip explanations, plus market regime classification with supporting signals
- **Research** — Research notes rendered as markdown
- **Expansion** — Expansion proposals with approve/reject controls
- **News** — Market headlines from yfinance with ticker badge filters, source attribution, and relative timestamps
- **Sentiment** — News sentiment scores and analysis per instrument
- **Risk** — Risk monitor alert history (stop-losses, trailing stops, take-profits, drawdowns, volatility, correlation) with stress test panel
- **Events** — Economic events calendar for the week ahead
- **Performance** — Weekly quantitative performance reports with visual metric cards (portfolio value, win rate, P&L, drawdown), adaptive score weights, and collapsible raw JSON
- **Reports** — Accordion list of daily morning reports
- **Reflections** — Agent self-assessments rendered as markdown
- **Tasks** — Manual task controls (run/stop) for all agents grouped by category, cron schedules, and execution history (auto-refreshes every 5s)
- **Chat** — Conversational interface for interrogating agents about their trading decisions

The frontend proxies all `/api/*` requests to the backend via Next.js rewrites.

## Project Structure

```
trader-app/
├── agent.py               # Core trading agent (LLM calls, trade execution, scoring framework,
│                          #   trailing stops, position sizing integration, performance feedback)
├── api.py                 # FastAPI REST API (all endpoints including technicals and regime)
├── compactor.py           # Memory compaction agent
├── config.py              # All configuration (instruments, regime params, scoring thresholds,
│                          #   position sizing, stop/take-profit settings, system prompt)
├── events_agent.py        # Economic events calendar agent
├── expansion.py           # Expansion analysis agent (new instrument proposals, user approval)
├── market_data.py         # Market data fetching via Finnhub + yfinance fallback, technical indicators
├── performance_analyst.py # Weekly quantitative performance agent + per-trade feedback generation
├── position_sizing.py     # Volatility-scaled position sizing (ATR-based, regime-adjusted)
├── rebalancer.py          # Weekly portfolio rebalancing agent
├── regime.py              # Market regime detection (6 regimes based on SPY technicals + VIX)
├── risk_monitor.py        # High-frequency risk monitoring with automatic trailing stop
│                          #   and take-profit execution
├── scheduler.py           # APScheduler setup (background + standalone modes)
├── score_weights.py       # Adaptive per-instrument scoring dimension weights
├── sentiment_agent.py     # News sentiment analysis agent
├── server.py              # FastAPI app with scheduler lifespan
├── stress_test.py         # Portfolio stress testing (scenario analysis)
├── entrypoint.sh          # Docker entrypoint (Ollama health check, command routing)
├── Dockerfile             # Python backend container
├── docker-compose.yml     # Multi-service orchestration
├── requirements.txt       # Python dependencies (includes pandas-ta)
├── research/              # Multi-source research engine
│   ├── adapters/          # 7 data source adapters (FRED, Finnhub, SEC EDGAR, etc.)
│   ├── pipeline.py        # Research orchestration
│   ├── clustering.py      # Narrative clustering
│   ├── ranking.py         # Item/cluster ranking heuristics
│   ├── summarizer.py      # LLM-based summarization
│   ├── models.py          # Domain models
│   ├── cache.py           # TTL cache
│   ├── dedup.py           # Deduplication
│   └── source_catalog.py  # Source trust metadata
├── tests/                 # Test suite
│   ├── test_adapters.py
│   ├── test_cache.py
│   ├── test_clustering.py
│   ├── test_dedup.py
│   ├── test_models.py
│   └── test_ranking.py
├── trader/                # Persistent data (volume-mounted)
│   ├── portfolio.json     # Portfolio state with trailing stops
│   ├── regime.json        # Current market regime
│   ├── approved_instruments.json
│   ├── expansion_proposals.json
│   ├── portfolio_history.json
│   ├── task_history.json
│   ├── trade_log.md
│   ├── reflections.md
│   ├── research.md
│   ├── sentiment.md
│   ├── risk_alerts.md
│   ├── performance.md
│   ├── events.md
│   ├── market_research.json
│   ├── market_brief.md
│   ├── expansion_proposals.json
│   └── reports/
└── web/                   # Next.js frontend
    ├── Dockerfile
    ├── next.config.js     # API proxy rewrites
    ├── package.json
    └── src/
        ├── app/           # Next.js App Router pages (11 routes)
        ├── components/    # React components (Dashboard, Technicals, Trades, Sentiment, etc.)
        └── lib/
            └── api.ts     # Typed API client
```
