"""FastAPI REST API for the day-trader agent."""
import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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
from regime import detect_regime, load_regime

logger = logging.getLogger(__name__)

app = FastAPI(title="Day Trader Agent API", version="1.0.0")

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

# Max entries to keep in the history file to prevent unbounded growth
_TASK_HISTORY_MAX = 500


def _load_task_history():
    """Load task history from disk on startup.
    Marks any entries left in 'running' state (from a previous crash) as interrupted."""
    global _task_history
    try:
        with open(config.TASK_HISTORY_PATH, "r") as f:
            _task_history = json.load(f)
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
    except (FileNotFoundError, json.JSONDecodeError):
        _task_history = []


def _save_task_history():
    """Persist task history to disk. Call with _task_lock held."""
    try:
        # Trim to max entries before saving
        trimmed = _task_history[-_TASK_HISTORY_MAX:]
        with open(config.TASK_HISTORY_PATH, "w") as f:
            json.dump(trimmed, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save task history: {e}")


# Load history from previous runs on import
_load_task_history()


def _run_task_in_thread(task_id: str, task_name: str, func):
    """Run an agent task in a background thread, tracking status."""
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
        entry["status"] = "completed"
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        entry["status"] = "failed"
        entry["error"] = str(e)
    finally:
        entry["finished_at"] = datetime.now().isoformat()
        with _task_lock:
            _running_tasks.pop(task_id, None)
            _save_task_history()


# ── Portfolio ──────────────────────────────────────────────

@app.get("/api/portfolio")
def get_portfolio():
    """Return current portfolio state."""
    try:
        return load_portfolio()
    except FileNotFoundError:
        raise HTTPException(404, "portfolio.json not found")


@app.get("/api/portfolio/history")
def get_portfolio_history(days: int = 30):
    """Return portfolio value history, optionally filtered to last N days."""
    try:
        with open(config.PORTFOLIO_HISTORY_PATH, "r") as f:
            history = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        history = []

    if days and history:
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=days)
        history = [
            s for s in history
            if datetime.fromisoformat(s["timestamp"]) >= cutoff
        ]

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


# ── Trade Log ──────────────────────────────────────────────

@app.get("/api/trades")
def get_trades(limit: int = 50):
    """Return parsed trade log entries."""
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
    "research": {"name": "Market Research", "func": run_research},
    "hourly_check": {"name": "Hourly Market Check", "func": run_hourly_check},
    "morning_report": {"name": "Morning Report", "func": run_morning_report},
    "compaction": {"name": "Memory Compaction", "func": run_compaction},
    "sentiment": {"name": "Sentiment Analysis", "func": run_sentiment},
    "risk_monitor": {"name": "Risk Monitor", "func": run_risk_monitor},
    "rebalancer": {"name": "Portfolio Rebalancer", "func": run_rebalancer},
    "performance": {"name": "Performance Analysis", "func": run_performance_analysis},
    "events": {"name": "Events Calendar", "func": run_events_calendar},
    "expansion": {"name": "Portfolio Expansion", "func": run_expansion_analysis},
}

TASK_CRON_MAP = {
    "research": config.RESEARCH_CRON,
    "hourly_check": config.HOURLY_CRON,
    "morning_report": config.MORNING_REPORT_CRON,
    "compaction": config.COMPACTION_CRON,
    "sentiment": config.SENTIMENT_CRON,
    "risk_monitor": config.RISK_MONITOR_CRON,
    "rebalancer": config.REBALANCER_CRON,
    "performance": config.PERFORMANCE_CRON,
    "events": config.EVENTS_CRON,
    "expansion": config.EXPANSION_CRON,
}


@app.get("/api/tasks")
def get_tasks():
    """Return status of all tasks including schedule info and history."""
    tasks = []
    for task_id, info in TASK_REGISTRY.items():
        # Find last run from history
        last_run = None
        for entry in reversed(_task_history):
            if entry["task_id"] == task_id:
                last_run = entry
                break

        is_running = task_id in _running_tasks and _running_tasks[task_id].is_alive()

        cron = TASK_CRON_MAP.get(task_id, "—")

        tasks.append({
            "task_id": task_id,
            "name": info["name"],
            "cron": cron,
            "is_running": is_running,
            "last_run": last_run,
        })
    return tasks


@app.get("/api/tasks/history")
def get_task_history(limit: int = 50):
    """Return recent task execution history."""
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
    """Request to stop a running task. Note: thread-based tasks can't be
    forcefully killed, but this marks them for cleanup."""
    with _task_lock:
        if task_id not in _running_tasks:
            raise HTTPException(404, f"Task {task_id} is not running")
        # We can't truly kill a thread in Python, but we remove tracking
        _running_tasks.pop(task_id, None)
    return {"status": "stop_requested", "task_id": task_id}


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
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


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


@app.get("/api/config")
def get_config_updated():
    """Return current agent configuration (non-sensitive)."""
    return {
        "model": config.TRADER_MODEL_NAME,
        "research_model": config.RESEARCH_MODEL,
        "report_model": config.REPORT_MODEL,
        "sentiment_model": config.SENTIMENT_MODEL,
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
