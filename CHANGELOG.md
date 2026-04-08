# Changelog

## 2026-04-08

### Added
- **Fractional share support** — the agent can now buy and sell fractional shares (e.g. 0.195 shares of SPY at $512.40 = $100 position). Positions are sized by dollar amount divided by share price, rounded to 3 decimal places. This eliminates the entire class of "position would exceed X% limit" rejections that blocked all trading on the $1,000 portfolio, since the agent can now buy exactly the dollar amount the percentage cap allows regardless of share price.
- **Portfolio vs benchmark feedback loop** (`benchmark.py`) — computes portfolio return vs SPY buy-and-hold over the same period, calculates alpha, average cash drag, and an annualized Sharpe-like ratio. Generates concrete actionable suggestions (e.g., "UNDERPERFORMING BENCHMARK: alpha -2.3%, consider deploying more capital") that are injected into every trading prompt. New instruction 9.1 tells the LLM to address benchmark underperformance explicitly. New API endpoint `GET /api/benchmark` exposes the metrics.
- **Market Check cycle budget** — the hourly check now tracks wall-clock elapsed time (`HOURLY_CHECK_TIMEOUT + 120s`). Before each non-essential LLM call (bear-case debate, closed-trade reflections, cycle reflection), it checks remaining budget and skips if time is running low. Prevents the cycle from blocking the next scheduled run. Elapsed time is logged at the end of each cycle.
- **`REPORT_TIMEOUT`** (default 600s) — dedicated timeout for the morning report LLM call, added to `config.py` and `docker-compose.yml`. Previously fell back to the 300s default `OLLAMA_TIMEOUT`.
- **Portfolio History range persisted in localStorage** — the selected time range (1D, 7D, 1M, etc.) on the Portfolio History chart is now saved to `localStorage` and restored on page load, so users don't have to reselect their preferred view each visit.

### Removed
- **1-share override and graduated absolute ceiling** — no longer needed now that fractional shares allow precise dollar-based sizing at any portfolio size.

### Fixed
- **Dashboard showing loss despite positive positions** — `total_value_usd` was only recalculated inside `execute_trade()`, which runs when a trade happens. The risk monitor updated position prices every 3 minutes but saved the portfolio with the stale total from the last trade. The dashboard could show a loss even when all open positions had positive unrealized gains. The risk monitor now recalculates `total_value_usd` = cash + Σ(quantity × current_price) after every price update cycle, and also updates `all_time_high` so the drawdown check works correctly.
- **GPU saturation from concurrent agents** — during market hours, Research (every 10 min), Market Check (every 30 min), Speculation (5x daily), and Sentiment (3x daily) all fired via APScheduler's default 20-thread pool. When crons overlapped, multiple threads hit Ollama simultaneously, keeping the GPU pegged at 100% with no idle window for the model to unload. Added a `threading.Lock` around `call_ollama()` so only one LLM request is in-flight at a time. Reduced the APScheduler thread pool from 20 to 4 workers.
- **Morning report timing out** — `run_morning_report()` called `call_ollama()` without an explicit timeout, falling back to the 300s default which was too short. Now uses `REPORT_TIMEOUT` (600s).
- **Market Check reflection calls missing explicit timeouts** — the closed-trade reflection and cycle reflection `call_ollama()` calls inside `run_hourly_check()` used the default 300s timeout. Now pass `config.OLLAMA_TIMEOUT` explicitly.
- **`max_pct` NameError in hourly check prompt** — the prompt string in `run_hourly_check()` referenced `max_pct`, a variable only defined in the separate `validate_trade()` function. Replaced with inline `regime_params.get('max_position_pct', config.MAX_POSITION_PCT)`.

## 2026-04-06 (proactive trading tuning)

### Added
- **Dynamic buy threshold** — when portfolio cash exceeds 70% (configurable via `HIGH_CASH_PCT`), the composite score buy threshold drops from 3 to 2 (configurable via `SCORE_BUY_THRESHOLD_HIGH_CASH`). The LLM prompt explicitly communicates the reduced threshold and encourages proactive capital deployment rather than waiting for perfect setups.
- **Intraday reversal detection** (`detect_intraday_reversal()`, `detect_intraday_reversals_all()`, `get_intraday_reversal_summary()` in `market_data.py`) — uses 5-minute intraday bars to detect when instruments recover ≥60% of their session range from the low. Reversal data is injected into the hourly trading prompt as a new "Intraday Reversal Scan" section with dedicated evaluation instructions (9.8).
- **Momentum pulse scanner** (`run_momentum_pulse()` in `market_data.py`) — lightweight data-only job (no LLM call) that runs every 10 minutes during market hours (10 AM–3 PM). Scans all instruments for intraday reversal signals and writes them to `momentum_pulse.json`. The hourly check reads this file and includes active signals in the prompt as "Momentum Pulse Signals."
- **Speculative trade threshold** — speculation-backed trades with reward/risk ≥ 2.0 can now use a reduced buy threshold of 2 (configurable via `SCORE_BUY_THRESHOLD_SPECULATIVE`) with a max position of 5% (configurable via `SPECULATION_MAX_POSITION_PCT`). The LLM must note "SPECULATIVE THRESHOLD APPLIED" in its reasoning when using this path.
- **Cash drag warning** (instruction 9.9 in trading prompt) — when cash exceeds the high-cash threshold, the prompt explicitly pressures the agent to look for the best available opportunity and reminds it that the cost of missing a reversal is real.
- **New config entries**: `SCORE_BUY_THRESHOLD_HIGH_CASH`, `HIGH_CASH_PCT`, `SCORE_BUY_THRESHOLD_SPECULATIVE`, `SPECULATION_MAX_POSITION_PCT`, `MOMENTUM_PULSE_CRON`, `MOMENTUM_PULSE_PATH`, `MOMENTUM_REVERSAL_RECOVERY_PCT`
- **New scheduled job**: `momentum_pulse` (Momentum Pulse, every 10 min during market hours)
- **New data file**: `trader/momentum_pulse.json` — latest momentum pulse scan results

### Changed
- **DOWNTREND regime multiplier** raised from 0.5 to 0.7 — gives the agent more risk budget to act during downtrends instead of being effectively paralyzed by tiny position sizes on a small portfolio.
- **DOWNTREND max position** raised from 10% to 12% — slightly more room to take meaningful positions during downtrends while still being conservative.
- **Speculation agent frequency** increased from 3x daily (10 AM, 1 PM, 3 PM) to 5x daily (10 AM, 11 AM, 1 PM, 2 PM, 3 PM) — closes the midday gap where intraday reversals were going unnoticed.
- Hourly trading prompt now includes three new sections: Intraday Reversal Scan, Momentum Pulse Signals, and Cash Efficiency warning.
- Scoring rules in the trading prompt now use the dynamic `effective_buy_threshold` instead of the static `SCORE_BUY_THRESHOLD`, with explicit messaging when the threshold is reduced.

## 2026-04-06 (scheduler reliability)

### Added
- **Speculation agent** (`speculation_agent.py`) — scans for asymmetric risk/reward setups the conservative trading agent might overlook. Runs 3x daily during market hours (10 AM, 1 PM, 3 PM ET). Produces 1-3 speculative theses with target %, stop %, reward/risk ratio (must be ≥1.5), confidence, timeframe, suggested position size (3-8%), and a concrete invalidation point. The trading agent reads these as a "Speculative Opportunities" section in its prompt and may use them as additional conviction — but still requires a passing composite score.
- **Startup catch-up** — when the container starts mid-day, agents whose cron fire time has already passed today (but haven't run) are scheduled for immediate catch-up execution, staggered by 10s intervals to avoid overwhelming Ollama. Example: container starts at 7:30 AM → compaction, events, market context, morning report, and rebalancer all fire within the first minute.

### Fixed
- **All cron day-of-week values were wrong** — APScheduler's `from_crontab()` uses ISO weekdays (0=Mon through 6=Sun), not standard cron (0=Sun through 6=Sat). Every schedule was shifted by one day: Mon–Fri jobs ran Tue–Sat, the Monday rebalancer ran Tuesday, Friday performance ran Saturday, and Sun–Thu overseas monitors ran Mon–Fri. All 17 crons corrected in `config.py`, `docker-compose.yml`, and the frontend day name display.
- **Agents not firing on schedule** — `misfire_grace_time` was 5–10 minutes, causing APScheduler to silently skip every job whose fire time had already passed when the container started (e.g., container starts at 6:37 AM, 5 AM compaction is 97 minutes late, well past the 10-minute grace). Increased to 2 hours for pre-market/weekly jobs, 1 hour for overseas monitors, 15–30 minutes for market-hours jobs. Added `coalesce=True` (no duplicate runs on catch-up) and `max_instances=1` (no overlapping runs).
- **Health endpoint now reports scheduler diagnostics** — thread state, job count, and next 3 fire times for debugging schedule issues

## 2026-04-06

### Added
- **Page descriptions** — every page in the web dashboard now has a beginner-friendly intro blurb explaining what it shows and why it matters (via new `PageDescription` component)
- **Learn page** (`/learn`) — comprehensive guide covering core investing concepts (portfolios, ETFs, bull/bear markets, risk management, technical analysis, diversification), the daily trading cycle as a step-by-step flow, all agent roles, and a glossary of 12 key terms (ATR, RSI, MACD, VIX, etc.)
- **Agent role descriptions on Tasks page** — each task card now shows a one-line description of what the agent does
- **Next run time on Tasks page** — each task card shows when the agent will fire next, pulled from the live APScheduler instance via new `next_run` field on `/api/tasks`

### Changed
- **Flattened project structure** — moved all files from `trader-app/` to the repository root; `docker compose` now runs from the root directory
- **All model assignments overridable from `.env`** — `docker-compose.yml` model vars changed from hardcoded values to `${VAR:-default}` interpolation so `.env` overrides are respected
- **Overseas monitor crons added to `docker-compose.yml`** — the 5 overseas schedules (Nikkei open/reopen/late, FTSE open, Europe handoff) were missing; now explicit and overridable from `.env`
- **Comprehensive README update** — architecture diagram (17 jobs), all agent tables, overseas signal queue docs, exchange calendar/DST, hypothesis tracking, bear-case debate, strategy tracking, updated API endpoints, project structure, and configuration sections

### Fixed
- **Ollama health check blocked API startup for 150s** — reduced from 30 retries × 5s to 5 retries × 2s; API starts regardless of Ollama availability, agent tasks fail gracefully on LLM calls
- **Missing `portfolio.json` caused 404/500 on Dashboard and Risk pages** — `load_portfolio()` now returns a default $1,000 portfolio instead of raising `FileNotFoundError`; entrypoint seeds the file on first run
- **Performance page crash on null `profit_factor`** — frontend called `.toFixed(2)` on `null` after the backend changed from `Infinity` to `None`; now displays ∞ for both
- **EVENTS_MODEL too slow** — reverted from `qwen3.5:latest` to `qwen2.5:7b` in `docker-compose.yml`; events calendar is a structured generation task that doesn't need deep reasoning
- **`overseas_signals.py` missing from Dockerfile** — container crashed with `ModuleNotFoundError` on startup
- **APScheduler executor logs suppressed** — uvicorn set third-party loggers to WARNING, hiding all job execution output; explicitly set APScheduler loggers to INFO so scheduled runs are visible in container logs
- **Cron time display showed "6 AM:55" instead of "6:55 AM"** — `cronToHuman()` placed minutes after the AM/PM suffix; added `fmtTime()` helper that formats correctly
- **`.gitignore` paths outdated after flatten** — updated from `trader-app/trader/` to `trader/`; added missing runtime data files (nikkei/ftse monitors, handoff, playbook, market context, strategy scores)

## 2026-04-04 (overseas trade signals)

### Added
- **Overseas trade signal queue** (`overseas_signals.py`) — new module that lets overseas monitors emit structured trade signals when they detect significant ETF moves (≥1.5% by default); signals carry direction, magnitude, driver explanation, urgency level, and optional suggested action; stale signals auto-pruned after 14 hours
- **Signal detection in monitors** — `run_nikkei_open()`, `run_nikkei_reopen()`, and `run_ftse_open()` now check EWJ/EWU/EWG price moves against the configurable threshold after each analysis cycle and emit signals for the U.S. trading agent; moves ≥3% are flagged as high-urgency with a suggested BUY/SELL
- **Hourly check consumes overseas signals** — `run_hourly_check()` reads pending signals, injects them into the trading prompt with dedicated evaluation instructions, and marks them as evaluated after the cycle; signals inform but do not bypass the standard composite scoring framework
- **Europe Handoff includes pending signals** — `run_europe_handoff()` now reads and synthesizes any pending trade signals into the pre-market briefing, with a new "Overseas Signal Assessment" section
- **API endpoint** `GET /api/overseas/signals` — returns pending and evaluated signals with counts
- **Config entries**: `OVERSEAS_SIGNAL_THRESHOLD_PCT` (default 1.5%), `OVERSEAS_SIGNAL_MAX_AGE_HOURS` (default 14h), `OVERSEAS_SIGNALS_PATH`

### Changed
- Hourly trading prompt instructions expanded with section 10.5 covering overseas signal evaluation rules: standard scoring still required, high-urgency signals evaluated first, ETF gap-pricing staleness check, per-signal audit trail in analysis output

### Fixed
- **Performance analyst timeout** — both performance reports showed `read timeout=300` because the running container predated the extended timeout fix; added dedicated `PERFORMANCE_TIMEOUT` (default 900s) so the performance analyst gets its own generous timeout independent of `RESEARCH_TIMEOUT`; updated `docker-compose.yml` and `.env`
- **`profit_factor: Infinity` in metrics JSON** — replaced `float("inf")` with `None` when no losing trades exist; `Infinity` is not valid standard JSON and could break downstream parsers
- **`.env` / `docker-compose.yml` model mismatch** — `.env` had `EVENTS_MODEL=qwen2.5:7b` while `docker-compose.yml` had `qwen3.5:latest`; synced `.env` to match

## 2026-04-04 (review fixes)

### Fixed
- **Bug: strategy scorer received sell price instead of entry price** — `execute_trade()` now stashes `pos["entry_price"]` as `trade["_entry_price"]` in the SELL branch before the position is removed from the list; `update_strategy_scores()` receives the correct cost basis so win/loss P&L percentages are accurate
- **Bug: `PLAYBOOK_CRON` ran before `PERFORMANCE_CRON` on Fridays** — moved from 5:30 AM to 6:30 AM so the playbook curator always reads the freshly-generated performance analysis from that morning (both config.py default and docker-compose.yml updated)
- **Bug: `timeout or config.OLLAMA_TIMEOUT` evaluates to 300 when timeout=0** — replaced `or` fallback with explicit `None` check (`timeout if timeout is not None else config.OLLAMA_TIMEOUT`) in `call_ollama()`; prevents any zero-valued env var from silently falling through to the shorter default timeout
- **Performance reports still show `read timeout=300`** — root cause is the running container predates the `think: false` and `RESEARCH_TIMEOUT=600` changes; requires `docker compose up -d --build` to deploy; old `[ERROR]` entries in `performance.md` persist until a successful run pushes them out of the top-5 view
- **Scheduler missing new agents** — `playbook` and `market_context` were registered in the API task registry but absent from `scheduler.py` JOBS list; they appeared in the Tasks UI but never fired automatically (fixed in previous commit `8416b02`)

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
