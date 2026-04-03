# Changelog

## 2026-04-03

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
