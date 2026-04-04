# Changelog

## 2026-04-04 (intelligence upgrade)

### Added
- **OBV (On-Balance Volume) trend** added to all instrument technicals — reports ACCUMULATING / DISTRIBUTING / NEUTRAL based on 10-day OBV slope; surface smart-money divergence from price action
- **VIX term structure** (`fetch_vix_term_structure()`, `get_vix_term_structure_summary()`) — fetches VIX spot and VIX3M, computes spread and classifies as NORMAL / FLAT / MILDLY_INVERTED / INVERTED; injected into every hourly trading prompt
- **30-day rolling correlation matrix** (`fetch_correlation_matrix()`, `get_correlation_summary()`) — computes pairwise return correlations across all instruments; flags high-correlation pairs (|r| ≥ 0.85) as concentration risk; injected into hourly prompt
- **`strategy_tracker.py`** — classifies every trade into one of 9 strategy categories (vix_spike_rotation, sector_rotation, momentum_continuation, mean_reversion, sector_divergence, contrarian_breakout, event_catalyst, stop_management, take_profit) using reasoning-text keyword matching; tracks win/loss/neutral counts, win rate, and total P&L per strategy; auto-suspends strategies with ≥10 trades and <35% win rate; suspended strategies flagged in every trading prompt
- **`playbook_agent.py`** — weekly Playbook Curator agent that reads all trade history and reflections, extracts recurring patterns with empirical win rates, and writes a structured `playbook.md`; the trading agent reads this every cycle as institutional memory; low-sample patterns (3–7 trades) explicitly flagged as hypotheses
- **`market_context.py`** — rolling 30-day Market Context agent that computes and caches portfolio arc, regime transitions, trade statistics, best/worst instruments, and correlation structure; written to `market_context.md` and injected into every hourly trading prompt
- **Hypothesis tracking** — all BUY trades now require structured hypothesis fields in the JSON output: `hypothesis` (what must be true), `falsified_by` (what would prove it wrong), `confidence` (High/Medium/Low), `horizon` (expected timeframe); stored in trade_log.md; reflections now explicitly evaluate whether the hypothesis was validated or falsified
- **Adversarial bear-case debate** — for BUY trades exceeding `BEAR_CASE_THRESHOLD_PCT` (default 5%) of portfolio value, a skeptical risk-analyst agent argues the strongest case against the trade before execution; the bear case is appended to the trade's reasoning in the log so the agent can learn from cases where valid counter-arguments were ignored
- **Confidence-gated temperature** — `get_adaptive_temperature()` in `playbook_agent.py` returns T=0.1 when high-confidence playbook patterns exist (≥65% win rate, 8+ trades), config default T=0.3 for mixed history, and T=0.6 when no applicable patterns exist (explore more freely in novel market conditions); applied to every hourly LLM call
- **`call_ollama()` temperature override** — new optional `temperature` parameter allows per-call temperature override while keeping the model-level `think` flag logic intact
- **New API endpoints**: `GET /api/playbook`, `GET /api/strategy-scores`, `GET /api/market-context`
- **New agents registered**: `playbook` (Strategy Playbook, Maintenance category), `market_context` (Market Context, Intelligence category)
- **New scheduled crons**: `PLAYBOOK_CRON` (5:30 AM Fridays), `MARKET_CONTEXT_CRON` (6:55 AM weekdays)
- **Strategy classification** written to every trade log entry as `- **Strategy:** [category]`
- **Strategy score ladder** injected into every hourly trading prompt as a markdown table

### Changed
- Hourly trading prompt expanded with: VIX term structure section, correlation matrix section, rolling 30-day market context section, strategy playbook section, strategy score ladder, suspended strategy warnings
- OBV trend added to `get_technicals_summary()` output line for each instrument
- Trading instructions updated to reference OBV divergence, VIX inversion signals, correlation concentration rule, playbook pattern matching, and suspended strategy avoidance
- Reflection prompts now evaluate hypothesis correctness explicitly (was the hypothesis validated or falsified, and why?)
- Closed-trade reflections extended from 3–5 sentences to 4–6 sentences to accommodate hypothesis evaluation

### Fixed
- Disabled Qwen3 thinking mode (`think: false`) for all non-trading-agent LLM calls to prevent timeouts on events and performance agents
- Added explicit `RESEARCH_TIMEOUT=600` and `EVENTS_TIMEOUT=600` to docker-compose.yml to prevent shell environment from overriding with the shorter `OLLAMA_TIMEOUT` default
- Risk Alerts on the Risks tab capped at 5 entries (was 30) so the Stress Test section is no longer buried

### Fixed
- Fixed technical indicator tooltip bubbles not appearing on hover — tooltip now renders below the header (inside the overflow area) and includes a native `title` fallback
- Fixed performance reports rendering raw JSON instead of human-readable metrics — metrics now display as a visual card grid with collapsible raw JSON; LLM errors show a clear warning banner
- Fixed task stop button returning 404 for scheduler-started tasks
- Fixed manually triggered tasks stuck as RUNNING forever due to `_sync_task_history()` orphaning in-memory entry references
- Fixed Docker build failures from ESLint `simple-import-sort` errors and vitest/vite type mismatch
- Fixed backend crash (`ModuleNotFoundError: overseas_monitors`) — added missing modules to Dockerfile COPY

### Added
- Finnhub real-time quotes — `get_finnhub_quote()` in `market_data.py` as Level 0 price source before yfinance fallback; uses Finnhub `h`/`l`/`d`/`dp` fields for high, low, change, change percent on ETFs
- Task category grouping on both the Tasks page and Dashboard Scheduled Tasks table — agents organized under Overseas Monitors, Core Trading, Intelligence, Risk & Portfolio, and Maintenance
- Shared `groupTasksByCategory()` utility and `TASK_CATEGORY_ORDER` constant in `lib/constants.ts`
- Task cancellation system — stop button sets a flag checked by `call_ollama` before each LLM request; `TaskCancelledError` propagates through scheduler and API wrappers
- Performance analyst retries once on LLM failure before writing the error to the report

### Changed
- Moved README to repository root
- Updated README with current model assignments, Finnhub market data, expansion agent, missing API endpoints, and dashboard views
- Removed obsolete `day_trader_agent_setup.md`

## 2026-04-03

### Added
- Overseas market monitoring: Nikkei Open Monitor (Tokyo morning session, 7–10:30 PM ET Sun–Thu), Nikkei Reopen Monitor (Tokyo afternoon / Asia continuation, 11 PM–2:30 AM ET), and FTSE Open Monitor (London open, 2:30–5:30 AM ET Mon–Fri)
- New `overseas_monitors.py` module with `run_nikkei_open()`, `run_nikkei_reopen()`, and `run_ftse_open()` agents following the existing agent pattern
- Follow-the-sun workflow: Asia → Europe → U.S. agents run in sequence; downstream agents consume upstream summaries via file-based handoff
- Europe Handoff Summary agent (`run_europe_handoff()`) — runs at 5:30 AM ET Mon–Fri, synthesizes full Asia + Europe overnight data into a single consolidated pre-market brief; downstream agents (Morning Report, Market Check, Chat) prefer the handoff summary when available, falling back to raw feeds
- Exchange calendar and DST utility module (`exchange_calendar.py`) — holiday calendars for JPX, LSE, and NYSE (2026–2027); `is_exchange_open()` / `is_exchange_holiday()` helpers; DST-offset computation (`get_et_offset_to()`, `is_dst_transition_week()`, `get_schedule_drift_warning()`); `get_current_session_info()` for API status
- Overseas monitors now skip runs on exchange holidays (JPX for Nikkei, LSE for FTSE) and log DST drift warnings when U.S. or UK transitions are within ±7 days
- Morning Report now includes Asia Overnight Recap, Europe-at-Open Recap, and Cross-Market Handoff Summary sections
- Market Check now ingests Nikkei and FTSE monitor summaries as cross-market context for trading decisions
- Risk Monitor now reads overseas summaries (preferring handoff) and logs exchange open/closed status and DST drift
- Chat context now includes overseas data (preferring handoff summary)
- API endpoints: `GET /api/overseas/nikkei`, `GET /api/overseas/ftse`, `GET /api/overseas/handoff`, `GET /api/exchange-calendar`
- Config entries: `NIKKEI_OPEN_CRON`, `NIKKEI_REOPEN_CRON`, `NIKKEI_REOPEN_LATE_CRON`, `FTSE_OPEN_CRON`, `EUROPE_HANDOFF_CRON`, `OVERSEAS_MODEL`, `OVERSEAS_TIMEOUT`
- File paths: `nikkei_monitor.md`, `ftse_monitor.md`, `handoff_summary.md` in the data directory

### Changed
- Expansion proposals list now sorts pending items to the top, then by newest first
- Nav bar shows a yellow dot indicator next to "Expansion" when pending proposals are available (polled every 60s)
- Scheduler JOBS list reordered to reflect follow-the-sun execution order (overseas → pre-market → market hours → weekly)
- Morning Report prompt expanded from 6 sections to 9 sections including global market context

### Fixed
- Fixed performance analyst timing out — now passes `RESEARCH_TIMEOUT` (600s) to `call_ollama` instead of defaulting to 300s

### Fixed
- Fixed events calendar agent timing out during research — switched `EVENTS_MODEL` from `qwen3.5:latest` to `qwen2.5:7b` (faster for structured generation) and added configurable `EVENTS_TIMEOUT` (default 600s)
- Fixed research agent timing out — added configurable `RESEARCH_TIMEOUT` (default 600s) applied to both LLM calls in the research cycle (summarizer + main analysis)
- Fixed scheduled tasks dashboard not staying in sync with actual executions — API was serving task status from a stale in-memory snapshot; both `/api/tasks` and `/api/tasks/history` now re-read from disk before responding so scheduler-triggered runs are reflected immediately
- Fixed `portfolio.json` being tracked by git despite `.gitignore` rule — removed from git index
- Fixed chat endpoint returning 500 — Next.js middleware `rewrite()` was stripping POST request bodies; middleware now explicitly proxies non-GET requests via `fetch` to preserve bodies
- Fixed Market Check failing with `No module named 'score_weights'` — moved import inside a try/except so it degrades gracefully before Docker rebuild
- Fixed task status showing IDLE while task is running when triggered by the scheduler — `is_running` now also checks the latest task history entry status
- Fixed position chart 500 error on 1M range — replaced unreliable yfinance `period` parameter with explicit `start`/`end` date range
- Fixed position chart 500 error from numpy/pandas serialization — added explicit `float()` casts and fixed `row.get()` on pandas Series
- Fixed scheduled tasks (research, sentiment, etc.) never firing — lifespan was set via `app.router.lifespan_context` after construction, which FastAPI silently ignores; moved lifespan into the `FastAPI()` constructor so the background scheduler actually starts
- Fixed 500 Internal Server Error when running in Docker — Next.js standalone mode does not support `rewrites()` in `next.config.js`; added `middleware.ts` to proxy `/api/*` requests to the backend
- Fixed Technicals page stuck on loading spinner — `getRegime()` failure no longer blocks `getTechnicals()` from rendering
- Fixed portfolio history chart showing identical data for all time ranges — backend now uses timezone-aware date filtering

### Added
- Finnhub real-time quotes — new `get_finnhub_quote()` in `market_data.py` calls the `/quote` endpoint as a Level 0 price source before the existing yfinance fallback chain; `fetch_instrument_prices()` uses Finnhub's `h`/`l`/`d`/`dp` fields for high, low, change, and change percent when available, still falling back to yfinance for 5-day momentum and volume; only attempted for the 20 ETF tickers in `INSTRUMENTS` (indices are skipped to avoid Finnhub symbol-format mismatches); gracefully degrades when `FINNHUB_API_KEY` is unset, the price is zero, or the API returns 429
- Real-time intraday prices — `fetch_instrument_prices()` and `fetch_index_levels()` now use a three-level fallback (`fast_info` → 1m bar → daily close) with a `price_source` field for data freshness visibility
- Adaptive score dimension weights — new `score_weights.py` module learns per-instrument weights from trade outcomes; weights are injected into the LLM prompt and displayed on the Performance page
- Portfolio stress test panel — three scenarios (SPY -5%, VIX spike to 30, tech sector rotation) with stop-breach detection, shown on the Risk page with 5-minute caching
- News page (`/news`) under Analysis — fetches market headlines from yfinance for key tickers with ticker badge filters, source attribution, and relative timestamps
- Clickable Open Positions on the Dashboard — clicking a position opens a price history chart modal with 1D/7D/1M/3M/6M/1Y ranges and entry price / trailing stop reference lines
- Chat interface (`/chat`) for interrogating agents about their trading decisions — gathers live portfolio, regime, trades, research, reflections, risk alerts, and events as context for each query
- Tooltip explanations on all technical indicator labels (VIX, RSI, SMA, MACD, ATR, Bollinger Bands, etc.) in the Technicals page with custom styled tooltips
- "Finished" column on the Scheduled Tasks table in the Dashboard showing when each task last completed
- Index tracker bar now appears at the top of every page (moved from Dashboard to root layout)
- Configurable Ollama timeout via `OLLAMA_TIMEOUT` env var (default 300s); `call_ollama` now accepts an optional `timeout` parameter so any agent can override the default
- Index tracker bar at the top of the Dashboard showing live data for S&P 500, NASDAQ, DOW, Nikkei 225, and FTSE 100 with price, direction arrow, change, and change percentage
- Dedicated model configuration for Events (`EVENTS_MODEL`) and Expansion (`EXPANSION_MODEL`) agents
- Portfolio chart now shows a hint when available data is shorter than the selected range, plus a data point count

### Changed
- Renamed "Hourly Market Check" to "Market Check" throughout (scheduler, API, prompts, logs) since the schedule is configurable and not necessarily hourly
- Reorganized navigation tabs into logical groups: Overview, Trading, Analysis, History, System
- Risk Alerts page now renders structured tables with color-coded severity badges instead of raw markdown text
- Upgraded model assignments across all agents to better match task complexity:
  - Research/Performance/Rebalancer: `qwen2.5:7b` → `qwen3.5:latest`
  - Events/Expansion: `qwen2.5:7b` → `qwen3.5:latest` (dedicated configs)
  - Sentiment: `qwen2.5:7b` → `llama3.1:8b`
  - Morning Report: `phi3:3.8b` → `qwen2.5:7b`
- Updated `.env.example` with all model configuration variables and descriptions
