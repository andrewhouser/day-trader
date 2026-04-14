"""FastAPI REST API for the day-trader agent."""
import json
import logging
import os
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
from agent import (
    load_portfolio,
    read_recent_entries,
    run_hourly_check,
    run_morning_report,
    run_research,
)
from compactor import run_compaction
from expansion import (
    get_proposals,
    get_proposal,
    approve_proposal,
    reject_proposal,
    run_expansion_analysis,
    load_approved_into_config,
)
from market_data import fetch_index_levels, fetch_instrument_prices, fetch_technical_indicators
from sentiment_agent import run_sentiment
from risk_monitor import run_risk_monitor
from rebalancer import run_rebalancer
from performance_analyst import run_performance_analysis
from events_agent import run_events_calendar
from playbook_agent import run_playbook_update
from market_context import update_market_context
from regime import detect_regime, load_regime
from overseas_monitors import run_nikkei_open, run_nikkei_reopen, run_ftse_open, run_europe_handoff
from speculation_agent import run_speculation

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application):
    """Start scheduler on startup, shut down on exit."""
    from scheduler import start_background_scheduler
    logger.info("Loading user-approved instruments...")
    load_approved_into_config()
    logger.info("Starting background scheduler alongside API...")
    scheduler = start_background_scheduler()
    yield
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")


app = FastAPI(title="Day Trader Agent API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Track running tasks and their history
_running_tasks: dict[str, threading.Thread] = {}
_task_history: list[dict] = []
_task_lock = threading.Lock()
_cancelled_tasks: set[str] = set()

# Max entries to keep in the history file to prevent unbounded growth
_TASK_HISTORY_MAX = 500


def _read_task_history_from_disk() -> list[dict]:
    """Read task history directly from disk (picks up scheduler writes)."""
    try:
        with open(config.TASK_HISTORY_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _load_task_history():
    """Load task history from disk on startup.
    Marks any entries left in 'running' state (from a previous crash) as interrupted."""
    global _task_history
    _task_history = _read_task_history_from_disk()
    # Fix stale "running" entries from a previous process
    dirty = False
    for entry in _task_history:
        if entry.get("status") == "running":
            entry["status"] = "interrupted"
            entry["error"] = "Process restarted before task completed"
            entry["finished_at"] = entry.get("started_at")
            dirty = True
    if dirty:
        _save_task_history()
    logger.info(f"Loaded {len(_task_history)} task history entries from disk")


def _sync_task_history():
    """Re-sync in-memory history from disk to pick up scheduler-written entries."""
    global _task_history
    _task_history = _read_task_history_from_disk()


def _save_task_history():
    """Persist task history to disk atomically. Call with _task_lock held.

    Writes to a temp file then os.replace()-s it into place so a Docker
    daemon kill mid-write cannot corrupt the history file.
    """
    import tempfile
    try:
        trimmed = _task_history[-_TASK_HISTORY_MAX:]
        dir_path = os.path.dirname(config.TASK_HISTORY_PATH)
        with tempfile.NamedTemporaryFile(
            mode="w", dir=dir_path, suffix=".tmp", delete=False
        ) as f:
            json.dump(trimmed, f, indent=2)
            tmp_path = f.name
        os.replace(tmp_path, config.TASK_HISTORY_PATH)
    except Exception as e:
        logger.error(f"Failed to save task history: {e}")


# Load history from previous runs on import
_load_task_history()


def is_task_cancelled(task_id: str) -> bool:
    """Check whether a stop has been requested for *task_id*.

    Importable by agent modules so long-running steps (e.g. LLM calls)
    can bail out early.
    """
    return task_id in _cancelled_tasks


def clear_task_cancelled(task_id: str):
    """Remove the cancellation flag (called when a new run starts)."""
    _cancelled_tasks.discard(task_id)


def _run_task_in_thread(task_id: str, task_name: str, func):
    """Run an agent task in a background thread, tracking status."""
    global _task_history
    from agent import set_current_task_id, TaskCancelledError
    clear_task_cancelled(task_id)
    set_current_task_id(task_id)
    start_time = datetime.now().isoformat()
    entry = {
        "task_id": task_id,
        "task_name": task_name,
        "status": "running",
        "started_at": start_time,
        "finished_at": None,
        "error": None,
    }
    with _task_lock:
        _task_history.append(entry)
        _save_task_history()

    try:
        func()
        final_status = "completed"
        final_error = None
    except TaskCancelledError:
        logger.info(f"Task {task_id} was cancelled by user")
        final_status = "cancelled"
        final_error = "Stopped by user"
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        final_status = "failed"
        final_error = str(e)
    finally:
        set_current_task_id(None)
        finished_at = datetime.now().isoformat()
        with _task_lock:
            _running_tasks.pop(task_id, None)
            # Re-read from disk and update the matching entry so that
            # concurrent _sync_task_history() calls can't orphan our
            # in-memory reference (the entry we appended above may no
            # longer be in _task_history if _sync replaced the list).
            _task_history = _read_task_history_from_disk()
            for h in reversed(_task_history):
                if h["task_id"] == task_id and h["started_at"] == start_time:
                    h["status"] = final_status
                    h["finished_at"] = finished_at
                    h["error"] = final_error
                    break
            _save_task_history()


# ── Portfolio ──────────────────────────────────────────────

@app.get("/api/portfolio")
def get_portfolio():
    """Return current portfolio state."""
    return load_portfolio()


@app.get("/api/portfolio/history")
def get_portfolio_history(days: int = 30):
    """Return portfolio value history, optionally filtered to last N days."""
    from datetime import timedelta, timezone
    try:
        with open(config.PORTFOLIO_HISTORY_PATH, "r") as f:
            history = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        history = []

    if days and history:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=days)
        filtered = []
        for s in history:
            ts = datetime.fromisoformat(s["timestamp"])
            # Treat naive timestamps as UTC for consistent comparison
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= cutoff:
                filtered.append(s)
        history = filtered

    return history


# ── Market Data ────────────────────────────────────────────

@app.get("/api/market/indices")
def get_indices():
    """Return current index levels."""
    return fetch_index_levels()


@app.get("/api/market/instruments")
def get_instruments():
    """Return current instrument prices."""
    return fetch_instrument_prices()


@app.get("/api/market/technicals")
def get_technicals():
    """Return technical indicators for all instruments."""
    return fetch_technical_indicators()


@app.get("/api/market/regime")
def get_regime():
    """Return the current market regime classification."""
    return load_regime()


@app.get("/api/market/history/{ticker}")
def get_ticker_history(ticker: str, days: int = 30):
    """Return historical price data for a single ticker."""
    import yfinance as yf
    from datetime import timedelta

    interval_map = {1: "5m", 7: "15m", 30: "1d", 90: "1d", 180: "1d", 365: "1wk"}
    interval = interval_map.get(days, "1d")

    try:
        t = yf.Ticker(ticker.upper())

        # For 1D, use period-based fetch — start/end date strings exclude
        # intraday data for the current session, and index symbols (^GSPC etc.)
        # often return empty with start/end + 5m interval.
        if days <= 1:
            hist = t.history(period="1d", interval="5m")
            if hist.empty:
                # Fallback: 5 days at 15m gives a usable intraday-like view
                hist = t.history(period="5d", interval="15m")
        elif days <= 7:
            hist = t.history(period="5d", interval="15m")
        else:
            end = datetime.now()
            start = end - timedelta(days=days)
            hist = t.history(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"), interval=interval)

        if hist.empty:
            raise HTTPException(404, f"No data for {ticker}")
        results = []
        for idx, row in hist.iterrows():
            results.append({
                "time": idx.isoformat(),
                "price": float(round(row["Close"], 2)),
                "high": float(round(row["High"], 2)),
                "low": float(round(row["Low"], 2)),
                "volume": int(row["Volume"]) if "Volume" in row and row["Volume"] else None,
            })
        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ticker history error for {ticker}: {e}")
        raise HTTPException(502, f"Failed to fetch history: {e}")


# ── News ───────────────────────────────────────────────────

_news_cache: dict = {"result": None, "timestamp": None}
_NEWS_CACHE_TTL = 300  # 5 minutes


def _fetch_news() -> list[dict]:
    """Fetch market news from yfinance for tracked instruments and indices."""
    import yfinance as yf
    from datetime import timezone

    seen_urls: set[str] = set()
    articles: list[dict] = []

    # Fetch news for key tickers (broad market + sectors)
    news_tickers = ["SPY", "QQQ", "DIA", "XLK", "XLE", "GLD", "TLT"]
    for sym in news_tickers:
        try:
            ticker = yf.Ticker(sym)
            news = ticker.news
            if not news:
                continue
            for item in news:
                content = item.get("content", {})
                url = content.get("canonicalUrl", {}).get("url", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                pub_date = content.get("pubDate", "")
                provider = content.get("provider", {}).get("displayName", "")
                title = content.get("title", "")

                # Extract related tickers from content
                tickers_mentioned = []
                for fin in content.get("finance", {}).get("stockTickers", []):
                    tickers_mentioned.append(fin.get("symbol", ""))

                if title:
                    articles.append({
                        "title": title,
                        "url": url,
                        "source": provider,
                        "published": pub_date,
                        "tickers": tickers_mentioned,
                        "related_query": sym,
                    })
        except Exception as e:
            logger.debug(f"News fetch failed for {sym}: {e}")

    # Sort by published date descending
    articles.sort(key=lambda a: a.get("published", ""), reverse=True)
    return articles[:50]


@app.get("/api/news")
def get_news():
    """Return latest market news headlines."""
    now = datetime.now()
    if (_news_cache["result"] is not None
            and _news_cache["timestamp"] is not None
            and (now - _news_cache["timestamp"]).total_seconds() < _NEWS_CACHE_TTL):
        return _news_cache["result"]

    articles = _fetch_news()
    result = {"articles": articles, "timestamp": now.isoformat()}
    _news_cache["result"] = result
    _news_cache["timestamp"] = now
    return result


# ── Trade Log ──────────────────────────────────────────────

@app.get("/api/trades")
def get_trades(limit: int = 50):
    """Return parsed trade log entries."""
    import re
    raw = read_recent_entries(config.TRADE_LOG_PATH, limit)
    sections = raw.split("\n---\n")
    entries = []
    for section in sections[1:]:  # skip header
        section = section.strip()
        if not section:
            continue
        entry = {"raw": section}
        for line in section.split("\n"):
            line = line.strip().lstrip("- ")
            if line.startswith("**Date:**"):
                entry["date"] = line.replace("**Date:**", "").strip()
            elif line.startswith("**Action:**"):
                entry["action"] = line.replace("**Action:**", "").strip()
            elif line.startswith("**Instrument:**"):
                entry["instrument"] = line.replace("**Instrument:**", "").strip()
            elif line.startswith("**Quantity:**"):
                entry["quantity"] = line.replace("**Quantity:**", "").strip()
            elif line.startswith("**Price:**"):
                entry["price"] = line.replace("**Price:**", "").strip()
            elif line.startswith("**Reasoning:**"):
                entry["reasoning"] = line.replace("**Reasoning:**", "").strip()
            elif line.startswith("**Realized P&L:**"):
                entry["realized_pnl"] = line.replace("**Realized P&L:**", "").strip()
            elif line.startswith("**Portfolio Balance:**"):
                entry["portfolio_balance"] = line.replace("**Portfolio Balance:**", "").strip()
        # Detect "No Action" entries
        if "No Action" in section.split("\n")[0]:
            entry["action"] = "NO_ACTION"
        # Fallback: extract date from header or anywhere in the section
        if "date" not in entry:
            m = re.search(r"(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})", section)
            if m:
                entry["date"] = m.group(1).replace("T", " ")
            else:
                m = re.search(r"(\d{4}-\d{2}-\d{2})", section)
                if m:
                    entry["date"] = m.group(1)
        entries.append(entry)
    entries.reverse()  # newest first
    return entries


# ── Reflections ────────────────────────────────────────────

@app.get("/api/reflections")
def get_reflections(limit: int = 20):
    """Return parsed reflections."""
    raw = read_recent_entries(config.REFLECTIONS_PATH, limit)
    sections = raw.split("\n---\n")
    entries = []
    for section in sections[1:]:
        section = section.strip()
        if not section:
            continue
        entries.append({"raw": section})
    entries.reverse()
    return entries


# ── Research ───────────────────────────────────────────────

@app.get("/api/research")
def get_research(limit: int = 20):
    """Return parsed research notes."""
    raw = read_recent_entries(config.RESEARCH_PATH, limit)
    sections = raw.split("\n---\n")
    entries = []
    for section in sections[1:]:
        section = section.strip()
        if not section:
            continue
        entries.append({"raw": section})
    entries.reverse()
    return entries


# ── Reports ────────────────────────────────────────────────

@app.get("/api/reports")
def list_reports():
    """List all available morning reports."""
    reports_dir = Path(config.REPORTS_DIR)
    if not reports_dir.exists():
        return []
    files = sorted(reports_dir.glob("*_report.md"), reverse=True)
    return [{"filename": f.name, "date": f.name.replace("_report.md", "")} for f in files]


@app.get("/api/reports/{filename}")
def get_report(filename: str):
    """Return the content of a specific report."""
    # Sanitize filename
    if "/" in filename or ".." in filename:
        raise HTTPException(400, "Invalid filename")
    report_path = Path(config.REPORTS_DIR) / filename
    if not report_path.exists():
        raise HTTPException(404, "Report not found")
    return {"filename": filename, "content": report_path.read_text()}


# ── Task Management ────────────────────────────────────────

TASK_REGISTRY = {
    "nikkei_open": {"name": "Nikkei Open Monitor", "func": run_nikkei_open, "category": "Overseas Monitors"},
    "nikkei_reopen": {"name": "Nikkei Reopen Monitor", "func": run_nikkei_reopen, "category": "Overseas Monitors"},
    "nikkei_reopen_late": {"name": "Nikkei Reopen Monitor (late)", "func": run_nikkei_reopen, "category": "Overseas Monitors"},
    "ftse_open": {"name": "FTSE Open Monitor", "func": run_ftse_open, "category": "Overseas Monitors"},
    "europe_handoff": {"name": "Europe Handoff Summary", "func": run_europe_handoff, "category": "Overseas Monitors"},
    "research": {"name": "Market Research", "func": run_research, "category": "Core Trading"},
    "hourly_check": {"name": "Market Check", "func": run_hourly_check, "category": "Core Trading"},
    "morning_report": {"name": "Morning Report", "func": run_morning_report, "category": "Core Trading"},
    "compaction": {"name": "Memory Compaction", "func": run_compaction, "category": "Maintenance"},
    "sentiment": {"name": "Sentiment Analysis", "func": run_sentiment, "category": "Intelligence"},
    "risk_monitor": {"name": "Risk Monitor", "func": run_risk_monitor, "category": "Risk & Portfolio"},
    "rebalancer": {"name": "Portfolio Rebalancer", "func": run_rebalancer, "category": "Risk & Portfolio"},
    "performance": {"name": "Performance Analysis", "func": run_performance_analysis, "category": "Maintenance"},
    "events": {"name": "Events Calendar", "func": run_events_calendar, "category": "Intelligence"},
    "expansion": {"name": "Portfolio Expansion", "func": run_expansion_analysis, "category": "Risk & Portfolio"},
    "playbook": {"name": "Strategy Playbook", "func": run_playbook_update, "category": "Maintenance"},
    "market_context": {"name": "Market Context", "func": update_market_context, "category": "Intelligence"},
    "speculation": {"name": "Speculation Analysis", "func": run_speculation, "category": "Intelligence"},
}

TASK_CRON_MAP = {
    "nikkei_open": "NIKKEI_OPEN_CRON",
    "nikkei_reopen": "NIKKEI_REOPEN_CRON",
    "nikkei_reopen_late": "NIKKEI_REOPEN_LATE_CRON",
    "ftse_open": "FTSE_OPEN_CRON",
    "europe_handoff": "EUROPE_HANDOFF_CRON",
    "research": "RESEARCH_CRON",
    "hourly_check": "HOURLY_CRON",
    "morning_report": "MORNING_REPORT_CRON",
    "compaction": "COMPACTION_CRON",
    "sentiment": "SENTIMENT_CRON",
    "risk_monitor": "RISK_MONITOR_CRON",
    "rebalancer": "REBALANCER_CRON",
    "performance": "PERFORMANCE_CRON",
    "events": "EVENTS_CRON",
    "expansion": "EXPANSION_CRON",
    "playbook": "PLAYBOOK_CRON",
    "market_context": "MARKET_CONTEXT_CRON",
    "speculation": "SPECULATION_CRON",
}


def _get_task_cron(task_id: str) -> str:
    """Get the current cron expression for a task from config (live value)."""
    attr = TASK_CRON_MAP.get(task_id)
    if attr:
        return getattr(config, attr, "—")
    return "—"


@app.get("/api/tasks")
def get_tasks():
    """Return status of all tasks including schedule info and history."""
    _sync_task_history()
    tasks = []
    for task_id, info in TASK_REGISTRY.items():
        # Find last run from history
        last_run = None
        for entry in reversed(_task_history):
            if entry["task_id"] == task_id:
                last_run = entry
                break

        is_running = (
            (task_id in _running_tasks and _running_tasks[task_id].is_alive())
            or (last_run is not None and last_run.get("status") == "running")
        )

        cron = _get_task_cron(task_id)

        # Get next scheduled run time from the live scheduler
        next_run = None
        try:
            from scheduler import get_scheduler
            sched = get_scheduler()
            if sched:
                job = sched.get_job(task_id)
                if job and job.next_run_time:
                    next_run = job.next_run_time.isoformat()
        except Exception:
            pass

        tasks.append({
            "task_id": task_id,
            "name": info["name"],
            "category": info.get("category", "Other"),
            "cron": cron,
            "is_running": is_running,
            "last_run": last_run,
            "next_run": next_run,
        })
    return tasks


@app.get("/api/tasks/history")
def get_task_history(limit: int = 50):
    """Return recent task execution history."""
    _sync_task_history()
    return list(reversed(_task_history[-limit:]))


@app.post("/api/tasks/{task_id}/run")
def invoke_task(task_id: str):
    """Manually trigger a task."""
    if task_id not in TASK_REGISTRY:
        raise HTTPException(404, f"Unknown task: {task_id}")

    with _task_lock:
        if task_id in _running_tasks and _running_tasks[task_id].is_alive():
            raise HTTPException(409, f"Task {task_id} is already running")

        info = TASK_REGISTRY[task_id]
        thread = threading.Thread(
            target=_run_task_in_thread,
            args=(task_id, info["name"], info["func"]),
            daemon=True,
        )
        _running_tasks[task_id] = thread
        thread.start()

    return {"status": "started", "task_id": task_id, "name": info["name"]}


@app.post("/api/tasks/{task_id}/stop")
def stop_task(task_id: str):
    """Request to stop a running task.

    Sets a cancellation flag that agent code checks before expensive
    operations (e.g. LLM calls).  Also marks the task-history entry as
    'cancelled' so the dashboard updates immediately.
    """
    if task_id not in TASK_REGISTRY:
        raise HTTPException(404, f"Unknown task: {task_id}")

    with _task_lock:
        # Check if the task is actually running (manual thread or scheduler)
        thread_alive = task_id in _running_tasks and _running_tasks[task_id].is_alive()
        history_running = any(
            e["task_id"] == task_id and e.get("status") == "running"
            for e in reversed(_task_history)
        )
        if not thread_alive and not history_running:
            raise HTTPException(409, f"Task {task_id} is not currently running")

        _cancelled_tasks.add(task_id)
        _running_tasks.pop(task_id, None)

        # Mark the latest running history entry as cancelled
        for entry in reversed(_task_history):
            if entry["task_id"] == task_id and entry.get("status") == "running":
                entry["status"] = "cancelled"
                entry["finished_at"] = datetime.now().isoformat()
                entry["error"] = "Stopped by user"
                break
        _save_task_history()

    return {"status": "stop_requested", "task_id": task_id}


# ── Schedule persistence ───────────────────────────────────

_SCHEDULE_OVERRIDES_PATH = os.path.join(config.DATA_DIR, "schedule_overrides.json")


def _load_schedule_overrides():
    """Load saved schedule overrides from disk and apply to config on startup."""
    try:
        with open(_SCHEDULE_OVERRIDES_PATH, "r") as f:
            overrides = json.load(f)
        for task_id, cron_expr in overrides.items():
            attr = TASK_CRON_MAP.get(task_id)
            if attr:
                setattr(config, attr, cron_expr)
        logger.info(f"Loaded {len(overrides)} schedule override(s) from disk")
    except (FileNotFoundError, json.JSONDecodeError):
        pass


def _save_schedule_override(task_id: str, cron_expr: str):
    """Persist a schedule override to disk."""
    try:
        with open(_SCHEDULE_OVERRIDES_PATH, "r") as f:
            overrides = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        overrides = {}
    overrides[task_id] = cron_expr
    with open(_SCHEDULE_OVERRIDES_PATH, "w") as f:
        json.dump(overrides, f, indent=2)


# Apply any saved overrides on startup
_load_schedule_overrides()


@app.put("/api/tasks/{task_id}/schedule")
def update_task_schedule(task_id: str, body: dict):
    """Update the cron schedule for a task. Expects {"cron": "..."}."""
    from apscheduler.triggers.cron import CronTrigger
    from scheduler import get_scheduler

    if task_id not in TASK_REGISTRY:
        raise HTTPException(404, f"Unknown task: {task_id}")

    attr = TASK_CRON_MAP.get(task_id)
    if not attr:
        raise HTTPException(400, f"Task {task_id} has no configurable schedule")

    cron_expr = body.get("cron", "").strip()
    if not cron_expr:
        raise HTTPException(400, "Missing 'cron' field")

    # Validate the cron expression
    try:
        trigger = CronTrigger.from_crontab(cron_expr, timezone=config.TIMEZONE)
    except (ValueError, KeyError) as e:
        raise HTTPException(400, f"Invalid cron expression: {e}")

    # Update config in memory
    setattr(config, attr, cron_expr)

    # Persist to disk
    _save_schedule_override(task_id, cron_expr)

    # Reschedule the running job
    scheduler = get_scheduler()
    if scheduler and scheduler.running:
        try:
            scheduler.reschedule_job(task_id, trigger=trigger)
            logger.info(f"Rescheduled {task_id} to '{cron_expr}'")
        except Exception as e:
            logger.error(f"Failed to reschedule {task_id}: {e}")
            raise HTTPException(500, f"Schedule saved but failed to reschedule: {e}")

    return {"task_id": task_id, "cron": cron_expr}


# ── Config / Status ────────────────────────────────────────

@app.get("/api/compaction/status")
def get_compaction_status():
    """Return file sizes and entry counts for compactable files."""
    def _file_info(path: str) -> dict:
        if not os.path.exists(path):
            return {"exists": False, "size_bytes": 0, "entries": 0}
        content = Path(path).read_text()
        entries = [s.strip() for s in content.split("\n---\n")[1:] if s.strip()]
        return {
            "exists": True,
            "size_bytes": os.path.getsize(path),
            "entries": len(entries),
        }

    return {
        "research": _file_info(config.RESEARCH_PATH),
        "trade_log": _file_info(config.TRADE_LOG_PATH),
        "reflections": _file_info(config.REFLECTIONS_PATH),
        "research_history": _file_info(config.RESEARCH_HISTORY_PATH),
        "trade_history": _file_info(config.TRADE_HISTORY_PATH),
        "lessons": _file_info(config.LESSONS_PATH),
    }


@app.get("/api/health")
def health():
    import threading
    from scheduler import get_scheduler
    sched = get_scheduler()
    sched_info = None
    if sched:
        sched_threads = [t.name for t in threading.enumerate() if "APScheduler" in t.name or "ThreadPool" in t.name]
        jobs = []
        for j in sched.get_jobs():
            jobs.append({"id": j.id, "next_run": j.next_run_time.isoformat() if j.next_run_time else None})
        sched_info = {
            "running": sched.running,
            "job_count": len(jobs),
            "threads": sched_threads,
            "next_3_jobs": sorted(jobs, key=lambda x: x["next_run"] or "")[:3],
        }
    all_threads = [{"name": t.name, "daemon": t.daemon, "alive": t.is_alive()} for t in threading.enumerate()]
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "scheduler": sched_info,
        "threads": all_threads,
    }


# ── New Agent Data ─────────────────────────────────────────

@app.get("/api/sentiment")
def get_sentiment(limit: int = 10):
    """Return recent sentiment analysis entries."""
    raw = read_recent_entries(config.SENTIMENT_PATH, limit)
    sections = raw.split("\n---\n")
    entries = []
    for section in sections[1:]:
        section = section.strip()
        if section:
            entries.append({"raw": section})
    entries.reverse()
    return entries


@app.get("/api/risk-alerts")
def get_risk_alerts(limit: int = 20):
    """Return recent risk monitor alerts."""
    raw = read_recent_entries(config.RISK_ALERTS_PATH, limit)
    sections = raw.split("\n---\n")
    entries = []
    for section in sections[1:]:
        section = section.strip()
        if section:
            entries.append({"raw": section})
    entries.reverse()
    return entries


@app.get("/api/performance")
def get_performance(limit: int = 5):
    """Return recent performance analysis reports."""
    raw = read_recent_entries(config.PERFORMANCE_PATH, limit)
    sections = raw.split("\n---\n")
    entries = []
    for section in sections[1:]:
        section = section.strip()
        if section:
            entries.append({"raw": section})
    entries.reverse()
    return entries


@app.get("/api/events")
def get_events():
    """Return the current events calendar."""
    try:
        with open(config.EVENTS_PATH, "r") as f:
            return {"content": f.read()}
    except FileNotFoundError:
        return {"content": "No events calendar generated yet."}


@app.get("/api/overseas/nikkei")
def get_nikkei_monitor(limit: int = 5):
    """Return recent Nikkei monitor entries."""
    raw = read_recent_entries(config.NIKKEI_MONITOR_PATH, limit)
    sections = raw.split("\n---\n")
    entries = []
    for section in sections[1:]:
        section = section.strip()
        if section:
            entries.append({"raw": section})
    entries.reverse()
    return entries


@app.get("/api/overseas/ftse")
def get_ftse_monitor(limit: int = 5):
    """Return recent FTSE monitor entries."""
    raw = read_recent_entries(config.FTSE_MONITOR_PATH, limit)
    sections = raw.split("\n---\n")
    entries = []
    for section in sections[1:]:
        section = section.strip()
        if section:
            entries.append({"raw": section})
    entries.reverse()
    return entries


@app.get("/api/overseas/handoff")
def get_handoff_summary(limit: int = 3):
    """Return recent Europe Handoff Summary entries."""
    raw = read_recent_entries(config.HANDOFF_SUMMARY_PATH, limit)
    sections = raw.split("\n---\n")
    entries = []
    for section in sections[1:]:
        section = section.strip()
        if section:
            entries.append({"raw": section})
    entries.reverse()
    return entries


@app.get("/api/overseas/signals")
def get_overseas_signals():
    """Return all overseas trade signals (pending and evaluated)."""
    from overseas_signals import _load_signals, _prune_stale
    signals = _prune_stale(_load_signals())
    pending = [s for s in signals if s.get("status") == "pending"]
    evaluated = [s for s in signals if s.get("status") == "evaluated"]
    return {"pending": pending, "evaluated": evaluated, "total": len(signals)}


@app.get("/api/playbook")
def get_playbook():
    """Return the current strategy playbook content."""
    try:
        with open(config.PLAYBOOK_PATH, "r") as f:
            return {"content": f.read()}
    except FileNotFoundError:
        return {"content": "No playbook generated yet. Run the Strategy Playbook agent to generate one."}


@app.get("/api/strategy-scores")
def get_strategy_scores():
    """Return per-strategy win/loss statistics."""
    from strategy_tracker import _load_scores
    return _load_scores()


@app.get("/api/market-context")
def get_market_context():
    """Return the rolling 30-day market context summary."""
    try:
        with open(config.MARKET_CONTEXT_PATH, "r") as f:
            return {"content": f.read()}
    except FileNotFoundError:
        return {"content": "No market context available yet. Run the Market Context agent to generate one."}


@app.get("/api/benchmark")
def get_benchmark():
    """Return portfolio vs SPY benchmark comparison."""
    from benchmark import compute_benchmark_comparison
    try:
        return compute_benchmark_comparison()
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/exchange-calendar")
def get_exchange_calendar_status():
    """Return current exchange session status, holidays, and DST info."""
    from exchange_calendar import get_current_session_info
    return get_current_session_info()


@app.get("/api/speculation")
def get_speculation(limit: int = 5):
    """Return recent speculation analysis entries."""
    raw = read_recent_entries(config.SPECULATION_PATH, limit)
    sections = raw.split("\n---\n")
    entries = []
    for section in sections[1:]:
        section = section.strip()
        if section:
            entries.append({"raw": section})
    entries.reverse()
    return entries


@app.get("/api/config")
def get_config_updated():
    """Return current agent configuration (non-sensitive)."""
    return {
        "model": config.TRADER_MODEL_NAME,
        "research_model": config.RESEARCH_MODEL,
        "report_model": config.REPORT_MODEL,
        "sentiment_model": config.SENTIMENT_MODEL,
        "events_model": config.EVENTS_MODEL,
        "expansion_model": config.EXPANSION_MODEL,
        "compaction_model": config.COMPACTION_MODEL,
        "ollama_url": config.OLLAMA_BASE_URL,
        "temperature": config.TEMPERATURE,
        "timezone": config.TIMEZONE,
        "research_cron": config.RESEARCH_CRON,
        "hourly_cron": config.HOURLY_CRON,
        "morning_report_cron": config.MORNING_REPORT_CRON,
        "sentiment_cron": config.SENTIMENT_CRON,
        "risk_monitor_cron": config.RISK_MONITOR_CRON,
        "rebalancer_cron": config.REBALANCER_CRON,
        "performance_cron": config.PERFORMANCE_CRON,
        "events_cron": config.EVENTS_CRON,
        "nikkei_open_cron": config.NIKKEI_OPEN_CRON,
        "nikkei_reopen_cron": config.NIKKEI_REOPEN_CRON,
        "ftse_open_cron": config.FTSE_OPEN_CRON,
        "europe_handoff_cron": config.EUROPE_HANDOFF_CRON,
        "playbook_cron": config.PLAYBOOK_CRON,
        "market_context_cron": config.MARKET_CONTEXT_CRON,
        "stop_loss_pct": config.STOP_LOSS_PCT,
        "opportunity_pct": config.OPPORTUNITY_PCT,
        "risk_volatility_threshold": config.RISK_VOLATILITY_THRESHOLD,
        "risk_max_drawdown_pct": config.RISK_MAX_DRAWDOWN_PCT,
        "instruments": config.INSTRUMENTS,
        "indices": config.INDICES,
        "max_position_pct": config.MAX_POSITION_PCT,
        "compaction_cron": config.COMPACTION_CRON,
        "compaction_model": config.COMPACTION_MODEL,
    }


# ── Multi-Source Research Engine ────────────────────────────

@app.get("/api/research/report")
def get_research_report():
    """Return the latest machine-readable market research report (JSON)."""
    try:
        with open(config.MARKET_RESEARCH_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"error": "No research report generated yet. Run the research task first."}
    except json.JSONDecodeError:
        raise HTTPException(500, "Research report file is corrupted")


@app.get("/api/research/brief")
def get_research_brief():
    """Return the latest human-readable market brief."""
    try:
        with open(config.MARKET_BRIEF_PATH, "r") as f:
            return {"content": f.read()}
    except FileNotFoundError:
        return {"content": "No market brief generated yet. Run the research task first."}


@app.get("/api/research/narratives")
def get_narratives():
    """Return the current narrative clusters from the latest research report."""
    try:
        with open(config.MARKET_RESEARCH_PATH, "r") as f:
            report = json.load(f)
        return report.get("top_narratives", [])
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        raise HTTPException(500, "Research report file is corrupted")


@app.get("/api/research/sources")
def get_research_sources():
    """Return the source catalog with trust metadata."""
    from research.source_catalog import SOURCE_CATALOG
    return {
        key: {
            "name": meta.name,
            "category": meta.category.value,
            "source_type": meta.source_type.value,
            "reliability": meta.reliability,
            "opinion_heavy": meta.opinion_heavy,
            "coverage_regions": meta.coverage_regions,
            "enabled": meta.enabled,
        }
        for key, meta in SOURCE_CATALOG.items()
    }


@app.get("/api/research/cache/stats")
def get_research_cache_stats():
    """Return research cache statistics."""
    from research.cache import research_cache
    return research_cache.stats()


@app.post("/api/research/cache/clear")
def clear_research_cache():
    """Clear the research cache."""
    from research.cache import research_cache
    research_cache.clear()
    return {"status": "cleared"}


@app.get("/api/score-weights")
def get_score_weights():
    """Return current adaptive score dimension weights."""
    from score_weights import _load_all, DEFAULT_WEIGHTS
    all_weights = _load_all()
    return {"weights": all_weights, "defaults": DEFAULT_WEIGHTS}


# ── Stress Test ────────────────────────────────────────────

_stress_cache: dict = {"result": None, "timestamp": None}
_STRESS_CACHE_TTL = 300  # 5 minutes


@app.get("/api/stress-test")
def get_stress_test():
    """Run portfolio stress test scenarios and return results."""
    from stress_test import run_stress_test

    now = datetime.now()
    if (_stress_cache["result"] is not None
            and _stress_cache["timestamp"] is not None
            and (now - _stress_cache["timestamp"]).total_seconds() < _STRESS_CACHE_TTL):
        return _stress_cache["result"]

    portfolio = load_portfolio()
    instruments = fetch_instrument_prices()
    technicals = fetch_technical_indicators()

    result = run_stress_test(portfolio, instruments, technicals)
    _stress_cache["result"] = result
    _stress_cache["timestamp"] = now
    return result


# ── Portfolio Expansion Proposals ──────────────────────────

@app.get("/api/expansion/proposals")
def list_proposals(status: str = ""):
    """Return expansion proposals, optionally filtered by status."""
    return get_proposals(status if status else None)


@app.get("/api/expansion/proposals/{proposal_id}")
def get_single_proposal(proposal_id: str):
    """Return a single proposal by ID."""
    proposal = get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(404, "Proposal not found")
    return proposal


@app.post("/api/expansion/proposals/{proposal_id}/approve")
def approve_single_proposal(proposal_id: str):
    """Approve a pending proposal — adds the instrument to the tradeable set."""
    proposal = approve_proposal(proposal_id)
    if not proposal:
        raise HTTPException(404, "Proposal not found")
    return proposal


@app.post("/api/expansion/proposals/{proposal_id}/reject")
def reject_single_proposal(proposal_id: str, reason: str = ""):
    """Reject a pending proposal."""
    proposal = reject_proposal(proposal_id, reason)
    if not proposal:
        raise HTTPException(404, "Proposal not found")
    return proposal


@app.get("/api/expansion/instruments")
def get_approved_instruments():
    """Return all currently tradeable instruments (core + approved expansions)."""
    return config.INSTRUMENTS


# ── Chat ───────────────────────────────────────────────────

CHAT_SYSTEM = (
    "You are the Day Trader Agent's analyst assistant. The user is the portfolio owner "
    "reviewing your trading decisions. Answer questions about positions, trades, research, "
    "risk, sentiment, and strategy using the context provided. Be specific — cite data, "
    "dates, prices, and reasoning. If you don't have enough context to answer, say so. "
    "Never fabricate trades or data."
)

CHAT_MODEL = os.getenv("CHAT_MODEL", None)  # Falls back to RESEARCH_MODEL
CHAT_TIMEOUT = int(os.getenv("CHAT_TIMEOUT", "300"))


def _build_chat_context() -> str:
    """Gather current agent state for the chat LLM context."""
    from agent import call_ollama, read_recent_entries

    sections = []

    # Portfolio
    try:
        portfolio = load_portfolio()
        positions = portfolio.get("positions", [])
        pos_summary = "\n".join(
            f"  {p['ticker']}: {p['quantity']} shares @ ${p['entry_price']:.2f} "
            f"(current ${p['current_price']:.2f}, P&L ${p['unrealized_pnl']:.2f})"
            for p in positions
        ) or "  No open positions."
        sections.append(
            f"### Portfolio\n"
            f"Cash: ${portfolio['cash_usd']:.2f} | "
            f"Total: ${portfolio['total_value_usd']:.2f} | "
            f"Trades: {portfolio.get('trade_count', 0)}\n{pos_summary}"
        )
    except Exception:
        sections.append("### Portfolio\nUnavailable.")

    # Regime
    try:
        regime_data = load_regime()
        if regime_data:
            params = regime_data.get("parameters", {})
            sections.append(
                f"### Market Regime\n{regime_data['regime']} — "
                f"{params.get('strategy_note', '')}"
            )
    except Exception:
        pass

    # Recent trades
    try:
        trades = read_recent_entries(config.TRADE_LOG_PATH, 10)
        if trades.strip():
            sections.append(f"### Recent Trades\n{trades}")
    except Exception:
        pass

    # Recent research
    try:
        research = read_recent_entries(config.RESEARCH_PATH, 3)
        if research.strip():
            sections.append(f"### Recent Research\n{research}")
    except Exception:
        pass

    # Recent reflections
    try:
        reflections = read_recent_entries(config.REFLECTIONS_PATH, 5)
        if reflections.strip():
            sections.append(f"### Recent Reflections\n{reflections}")
    except Exception:
        pass

    # Risk alerts
    try:
        risk = read_recent_entries(config.RISK_ALERTS_PATH, 5)
        if risk.strip():
            sections.append(f"### Risk Alerts\n{risk}")
    except Exception:
        pass

    # Events
    try:
        with open(config.EVENTS_PATH, "r") as f:
            events = f.read()[:2000]
        if events.strip():
            sections.append(f"### Upcoming Events\n{events}")
    except Exception:
        pass

    # Overseas market summaries
    try:
        handoff = read_recent_entries(config.HANDOFF_SUMMARY_PATH, 1)
        if handoff.strip():
            sections.append(f"### Overnight Handoff Summary\n{handoff}")
        else:
            asia = read_recent_entries(config.NIKKEI_MONITOR_PATH, 2)
            if asia.strip():
                sections.append(f"### Asia Overnight (Nikkei)\n{asia}")
            europe = read_recent_entries(config.FTSE_MONITOR_PATH, 2)
            if europe.strip():
                sections.append(f"### Europe at Open (FTSE)\n{europe}")
    except Exception:
        pass

    return "\n\n".join(sections)


class ChatRequest(BaseModel):
    message: str


@app.post("/api/chat")
def chat(body: ChatRequest):
    """Chat with the trading agent about its decisions."""
    from agent import call_ollama_direct

    message = body.message.strip()
    if not message:
        raise HTTPException(400, "Message is required")

    try:
        context = _build_chat_context()
    except Exception as e:
        logger.error(f"Chat context build failed: {e}")
        context = "Context unavailable."

    prompt = f"""The portfolio owner is asking you a question. Use the context below to answer.

{context}

---

User question: {message}"""

    model = CHAT_MODEL or config.RESEARCH_MODEL
    try:
        response = call_ollama_direct(prompt, system=CHAT_SYSTEM, model=model, timeout=CHAT_TIMEOUT)
    except Exception as e:
        logger.error(f"Chat LLM call failed: {e}")
        raise HTTPException(502, f"LLM request failed: {e}")

    if response.startswith("[ERROR]"):
        raise HTTPException(502, response)

    return {"response": response}


# ── Runtime Settings ───────────────────────────────────────

_SETTINGS_PATH = os.path.join(config.DATA_DIR, "settings_overrides.json")

# Map of setting key → (config attribute, type, min, max, description, group)
_SETTINGS_SCHEMA = {
    # Risk Management
    "stop_loss_pct": ("STOP_LOSS_PCT", float, 0.5, 20.0, "Stop-loss trigger (%)", "Risk Management"),
    "take_profit_partial_pct": ("TAKE_PROFIT_PARTIAL_PCT", float, 1.0, 50.0, "Partial take-profit at (%) gain", "Risk Management"),
    "take_profit_full_pct": ("TAKE_PROFIT_FULL_PCT", float, 2.0, 100.0, "Full take-profit at (%) gain", "Risk Management"),
    "risk_max_drawdown_pct": ("RISK_MAX_DRAWDOWN_PCT", float, 1.0, 25.0, "Portfolio drawdown alert (%)", "Risk Management"),
    "risk_budget_pct": ("RISK_BUDGET_PCT", float, 0.5, 10.0, "Risk budget per trade (%)", "Risk Management"),
    "crisis_cooldown_hours": ("CRISIS_COOLDOWN_HOURS", int, 1, 48, "Hours between crisis reviews", "Risk Management"),
    "trailing_stop_atr_multiplier": ("TRAILING_STOP_ATR_MULTIPLIER", float, 0.5, 5.0, "Trailing stop ATR multiplier", "Risk Management"),
    # Trading Aggressiveness
    "score_buy_threshold": ("SCORE_BUY_THRESHOLD", int, 1, 8, "Buy threshold (composite score)", "Trading Aggressiveness"),
    "score_sell_threshold": ("SCORE_SELL_THRESHOLD", int, -8, -1, "Sell threshold (composite score)", "Trading Aggressiveness"),
    "high_cash_pct": ("HIGH_CASH_PCT", float, 30.0, 95.0, "Cash % to trigger aggressive buying", "Trading Aggressiveness"),
    "temperature": ("TEMPERATURE", float, 0.0, 1.0, "LLM temperature (lower = conservative)", "Trading Aggressiveness"),
    "speculation_max_position_pct": ("SPECULATION_MAX_POSITION_PCT", float, 0.01, 0.20, "Max speculative position (%)", "Trading Aggressiveness"),
    "bear_case_threshold_pct": ("BEAR_CASE_THRESHOLD_PCT", float, 1.0, 25.0, "Bear-case debate trigger (%)", "Trading Aggressiveness"),
    # Overseas Signals
    "overseas_signal_threshold_pct": ("OVERSEAS_SIGNAL_THRESHOLD_PCT", float, 0.5, 10.0, "Overseas signal threshold (%)", "Overseas Signals"),
    "overseas_signal_max_age_hours": ("OVERSEAS_SIGNAL_MAX_AGE_HOURS", int, 1, 48, "Overseas signal max age (hours)", "Overseas Signals"),
    # Rebalancer
    "rebalancer_target_cash_pct": ("REBALANCER_TARGET_CASH_PCT", float, 5.0, 80.0, "Target cash allocation (%)", "Rebalancer"),
    "rebalancer_drift_threshold": ("REBALANCER_DRIFT_THRESHOLD", float, 2.0, 30.0, "Drift threshold before rebalance (%)", "Rebalancer"),
}


def _load_settings_overrides():
    """Load saved settings overrides from disk and apply to config."""
    try:
        with open(_SETTINGS_PATH, "r") as f:
            overrides = json.load(f)
        applied = 0
        for key, value in overrides.items():
            if key in _SETTINGS_SCHEMA:
                attr, typ, _, _, _, _ = _SETTINGS_SCHEMA[key]
                setattr(config, attr, typ(value))
                applied += 1
        if applied:
            logger.info(f"Loaded {applied} settings override(s) from disk")
    except (FileNotFoundError, json.JSONDecodeError):
        pass


# Apply on startup
_load_settings_overrides()


@app.get("/api/settings")
def get_settings():
    """Return all tunable settings with current values, bounds, and metadata."""
    groups: dict[str, list] = {}
    for key, (attr, typ, min_val, max_val, desc, group) in _SETTINGS_SCHEMA.items():
        current = getattr(config, attr)
        entry = {
            "key": key,
            "value": current,
            "type": "float" if typ is float else "int",
            "min": min_val,
            "max": max_val,
            "description": desc,
        }
        groups.setdefault(group, []).append(entry)
    return {"groups": groups}


@app.put("/api/settings")
def update_settings(body: dict):
    """Update one or more runtime settings. Expects {"key": value, ...}.

    Validates types and bounds, applies to config in memory, and persists to disk.
    """
    updates = body.get("settings", body)
    if not isinstance(updates, dict):
        raise HTTPException(400, "Expected a JSON object of settings")

    errors = []
    applied = {}

    for key, value in updates.items():
        if key not in _SETTINGS_SCHEMA:
            errors.append(f"Unknown setting: {key}")
            continue

        attr, typ, min_val, max_val, desc, _ = _SETTINGS_SCHEMA[key]

        try:
            typed_value = typ(value)
        except (ValueError, TypeError):
            errors.append(f"{key}: expected {typ.__name__}, got {type(value).__name__}")
            continue

        if typed_value < min_val or typed_value > max_val:
            errors.append(f"{key}: {typed_value} out of range [{min_val}, {max_val}]")
            continue

        setattr(config, attr, typed_value)
        applied[key] = typed_value

    # Persist all overrides to disk
    if applied:
        try:
            existing = {}
            try:
                with open(_SETTINGS_PATH, "r") as f:
                    existing = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            existing.update(applied)
            with open(_SETTINGS_PATH, "w") as f:
                json.dump(existing, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist settings: {e}")

    result = {"applied": applied}
    if errors:
        result["errors"] = errors
    return result
