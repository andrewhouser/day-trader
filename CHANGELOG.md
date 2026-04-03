# Changelog

## 2026-04-03

### Fixed
- Fixed events calendar agent timing out during research — switched `EVENTS_MODEL` from `qwen3.5:latest` to `qwen2.5:7b` (faster for structured generation) and added configurable `EVENTS_TIMEOUT` (default 600s)
- Fixed scheduled tasks dashboard not staying in sync with actual executions — API was serving task status from a stale in-memory snapshot; both `/api/tasks` and `/api/tasks/history` now re-read from disk before responding so scheduler-triggered runs are reflected immediately
- Fixed `portfolio.json` being tracked by git despite `.gitignore` rule — removed from git index
- Fixed scheduled tasks (research, sentiment, etc.) never firing — lifespan was set via `app.router.lifespan_context` after construction, which FastAPI silently ignores; moved lifespan into the `FastAPI()` constructor so the background scheduler actually starts
- Fixed 500 Internal Server Error when running in Docker — Next.js standalone mode does not support `rewrites()` in `next.config.js`; added `middleware.ts` to proxy `/api/*` requests to the backend
- Fixed Technicals page stuck on loading spinner — `getRegime()` failure no longer blocks `getTechnicals()` from rendering
- Fixed portfolio history chart showing identical data for all time ranges — backend now uses timezone-aware date filtering

### Added
- "Finished" column on the Scheduled Tasks table in the Dashboard showing when each task last completed
- Configurable Ollama timeout via `OLLAMA_TIMEOUT` env var (default 300s); `call_ollama` now accepts an optional `timeout` parameter so any agent can override the default
- Index tracker bar at the top of the Dashboard showing live data for S&P 500, NASDAQ, DOW, Nikkei 225, and FTSE 100 with price, direction arrow, change, and change percentage
- Dedicated model configuration for Events (`EVENTS_MODEL`) and Expansion (`EXPANSION_MODEL`) agents
- Portfolio chart now shows a hint when available data is shorter than the selected range, plus a data point count

### Changed
- Reorganized navigation tabs into logical groups: Overview, Trading, Analysis, History, System
- Risk Alerts page now renders structured tables with color-coded severity badges instead of raw markdown text
- Upgraded model assignments across all agents to better match task complexity:
  - Research/Performance/Rebalancer: `qwen2.5:7b` → `qwen3.5:latest`
  - Events/Expansion: `qwen2.5:7b` → `qwen3.5:latest` (dedicated configs)
  - Sentiment: `qwen2.5:7b` → `llama3.1:8b`
  - Morning Report: `phi3:3.8b` → `qwen2.5:7b`
- Updated `.env.example` with all model configuration variables and descriptions
