"""Scheduler for the day-trader agent using APScheduler.

Runs as a background scheduler inside the FastAPI process,
or standalone via `python scheduler.py`.
"""
import json
import logging
import signal
import sys
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

import config
from agent import run_hourly_check, run_morning_report, run_research
from compactor import run_compaction
from sentiment_agent import run_sentiment
from risk_monitor import run_risk_monitor
from rebalancer import run_rebalancer
from performance_analyst import run_performance_analysis
from events_agent import run_events_calendar
from expansion import run_expansion_analysis, load_approved_into_config
from overseas_monitors import run_nikkei_open, run_nikkei_reopen, run_ftse_open, run_europe_handoff
from playbook_agent import run_playbook_update
from market_context import update_market_context
from speculation_agent import run_speculation
from market_data import run_momentum_pulse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

_bg_scheduler: BackgroundScheduler | None = None

# Task history shared with the API — loaded lazily to avoid circular imports
_TASK_HISTORY_MAX = 500


def _get_task_history_path() -> str:
    return config.TASK_HISTORY_PATH


def _load_task_history() -> list[dict]:
    try:
        with open(_get_task_history_path(), "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_task_history(history: list[dict]):
    """Write task history atomically so a mid-write daemon kill can't corrupt it."""
    import os
    import tempfile
    try:
        trimmed = history[-_TASK_HISTORY_MAX:]
        path = _get_task_history_path()
        dir_path = os.path.dirname(path)
        with tempfile.NamedTemporaryFile(
            mode="w", dir=dir_path, suffix=".tmp", delete=False
        ) as f:
            json.dump(trimmed, f, indent=2)
            tmp_path = f.name
        os.replace(tmp_path, path)
    except Exception as e:
        logger.error(f"Failed to save task history: {e}")


def _tracked(task_id: str, task_name: str, func):
    """Wrap a task function to record execution in the shared task history."""
    def wrapper():
        from agent import set_current_task_id, TaskCancelledError
        set_current_task_id(task_id)
        # Clear any leftover cancellation flag from a previous run
        try:
            from api import clear_task_cancelled
            clear_task_cancelled(task_id)
        except ImportError:
            pass

        history = _load_task_history()
        entry = {
            "task_id": task_id,
            "task_name": task_name,
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "finished_at": None,
            "error": None,
        }
        history.append(entry)
        _save_task_history(history)

        try:
            func()
            entry["status"] = "completed"
        except TaskCancelledError:
            logger.info(f"Scheduled task {task_id} was cancelled by user")
            entry["status"] = "cancelled"
            entry["error"] = "Stopped by user"
        except Exception as e:
            logger.error(f"Scheduled task {task_id} failed: {e}")
            entry["status"] = "failed"
            entry["error"] = str(e)
        finally:
            set_current_task_id(None)
            entry["finished_at"] = datetime.now().isoformat()
            # Re-load in case manual runs happened concurrently
            history = _load_task_history()
            # Update the entry we added (find by started_at match)
            for h in reversed(history):
                if h["task_id"] == task_id and h["started_at"] == entry["started_at"]:
                    h["status"] = entry["status"]
                    h["finished_at"] = entry["finished_at"]
                    h["error"] = entry["error"]
                    break
            _save_task_history(history)

    wrapper.__name__ = func.__name__
    return wrapper


JOBS = [
    # ── Overseas monitors (follow-the-sun: Asia → Europe → U.S.) ──
    ("nikkei_open", "Nikkei Open Monitor", run_nikkei_open, "NIKKEI_OPEN_CRON", 3600),
    ("nikkei_reopen", "Nikkei Reopen Monitor", run_nikkei_reopen, "NIKKEI_REOPEN_CRON", 3600),
    ("nikkei_reopen_late", "Nikkei Reopen Monitor (late)", run_nikkei_reopen, "NIKKEI_REOPEN_LATE_CRON", 3600),
    ("ftse_open", "FTSE Open Monitor", run_ftse_open, "FTSE_OPEN_CRON", 3600),
    ("europe_handoff", "Europe Handoff Summary", run_europe_handoff, "EUROPE_HANDOFF_CRON", 3600),
    # ── U.S. pre-market ──
    ("compaction", "Memory Compaction", run_compaction, "COMPACTION_CRON", 7200),
    ("events", "Events Calendar", run_events_calendar, "EVENTS_CRON", 7200),
    ("morning_report", "Morning Report", run_morning_report, "MORNING_REPORT_CRON", 7200),
    # ── U.S. market hours ──
    ("research", "Market Research", run_research, "RESEARCH_CRON", 900),
    ("hourly_check", "Market Check", run_hourly_check, "HOURLY_CRON", 1800),
    ("sentiment", "Sentiment Analysis", run_sentiment, "SENTIMENT_CRON", 3600),
    ("risk_monitor", "Risk Monitor", run_risk_monitor, "RISK_MONITOR_CRON", 300),
    ("speculation", "Speculation Analysis", run_speculation, "SPECULATION_CRON", 3600),
    ("momentum_pulse", "Momentum Pulse", run_momentum_pulse, "MOMENTUM_PULSE_CRON", 300),
    # ── Weekly / periodic ──
    ("rebalancer", "Portfolio Rebalancer", run_rebalancer, "REBALANCER_CRON", 7200),
    ("performance", "Performance Analysis", run_performance_analysis, "PERFORMANCE_CRON", 7200),
    ("expansion", "Portfolio Expansion", run_expansion_analysis, "EXPANSION_CRON", 7200),
    ("playbook", "Strategy Playbook", run_playbook_update, "PLAYBOOK_CRON", 7200),
    ("market_context", "Market Context", update_market_context, "MARKET_CONTEXT_CRON", 7200),
]


def _add_jobs(scheduler):
    """Add all scheduled jobs to a scheduler instance."""
    for task_id, name, func, cron_attr, grace in JOBS:
        cron_expr = getattr(config, cron_attr)
        scheduler.add_job(
            _tracked(task_id, name, func),
            CronTrigger.from_crontab(cron_expr, timezone=config.TIMEZONE),
            id=task_id,
            name=name,
            misfire_grace_time=grace,
            coalesce=True,
            max_instances=1,
        )


def start_background_scheduler() -> BackgroundScheduler:
    """Start a non-blocking background scheduler (for use with FastAPI)."""
    global _bg_scheduler
    if _bg_scheduler and _bg_scheduler.running:
        return _bg_scheduler

    load_approved_into_config()

    _bg_scheduler = BackgroundScheduler(timezone=config.TIMEZONE)
    _add_jobs(_bg_scheduler)
    _bg_scheduler.start()

    # Ensure APScheduler executor logs are visible at INFO level
    logging.getLogger("apscheduler.executors").setLevel(logging.INFO)
    logging.getLogger("apscheduler.scheduler").setLevel(logging.INFO)

    # Log next fire times for verification
    logger.info("Background scheduler started")
    for task_id, name, _, cron_attr, _ in JOBS:
        job = _bg_scheduler.get_job(task_id)
        next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M %Z") if job and job.next_run_time else "N/A"
        logger.info(f"  {name}: {getattr(config, cron_attr)} → next: {next_run}")

    # Startup catch-up: if we're inside a job's active window and it hasn't
    # run today, fire it immediately so agents don't wait for the next tick.
    _run_startup_catchup(_bg_scheduler)

    return _bg_scheduler


def _run_startup_catchup(scheduler: BackgroundScheduler):
    """Check each job and schedule an immediate catch-up run if it was missed today."""
    from datetime import timedelta
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(config.TIMEZONE)
    now = datetime.now(tz)
    today = now.date()
    history = _load_task_history()

    # Build a set of task_ids that already ran today
    ran_today: set[str] = set()
    for entry in history:
        try:
            started = datetime.fromisoformat(entry["started_at"])
            if started.date() == today:
                ran_today.add(entry["task_id"])
        except (KeyError, ValueError):
            pass

    catchup_count = 0
    for task_id, name, func, cron_attr, grace in JOBS:
        if task_id in ran_today:
            continue

        # Check if the job's cron had a fire time earlier today that we missed
        cron_expr = getattr(config, cron_attr)
        trigger = CronTrigger.from_crontab(cron_expr, timezone=config.TIMEZONE)

        # Walk backward from now to find if there was a fire time today
        # by checking what the previous fire time would have been
        check_time = now - timedelta(seconds=1)
        prev_fire = trigger.get_next_fire_time(None, now.replace(hour=0, minute=0, second=0))

        if prev_fire and prev_fire.date() == today and prev_fire < now:
            # There was a fire time today before now that we missed
            delay = 5 + catchup_count * 10  # stagger to avoid overwhelming Ollama
            scheduler.add_job(
                _tracked(task_id, f"{name} (catch-up)", func),
                "date",
                run_date=now + timedelta(seconds=delay),
                id=f"{task_id}_catchup",
                name=f"{name} (catch-up)",
                misfire_grace_time=3600,
                max_instances=1,
            )
            logger.info(f"  ↳ Catch-up scheduled: {name} in {delay}s (missed {prev_fire.strftime('%H:%M')})")
            catchup_count += 1

    if catchup_count == 0:
        logger.info("  No catch-up runs needed — all jobs are current")


def get_scheduler() -> BackgroundScheduler | None:
    return _bg_scheduler


def main():
    """Standalone blocking mode (for running without the API)."""
    logger.info("=" * 60)
    logger.info("Day Trader Agent Starting (standalone scheduler)")
    logger.info(f"Model: {config.TRADER_MODEL_NAME} @ {config.OLLAMA_BASE_URL}")
    logger.info(f"Timezone: {config.TIMEZONE}")
    for task_id, name, _, cron_attr, _ in JOBS:
        logger.info(f"  {name}: {getattr(config, cron_attr)}")
    logger.info(f"Data directory: {config.DATA_DIR}")
    logger.info("=" * 60)

    scheduler = BlockingScheduler(timezone=config.TIMEZONE)
    _add_jobs(scheduler)

    def shutdown(signum, frame):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    main()
