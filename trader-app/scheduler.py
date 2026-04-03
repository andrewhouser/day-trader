"""Scheduler for the day-trader agent using APScheduler.

Runs as a background scheduler inside the FastAPI process,
or standalone via `python scheduler.py`.
"""
import logging
import signal
import sys

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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

_bg_scheduler: BackgroundScheduler | None = None


def _add_jobs(scheduler):
    """Add all scheduled jobs to a scheduler instance."""
    scheduler.add_job(
        run_research,
        CronTrigger.from_crontab(config.RESEARCH_CRON, timezone=config.TIMEZONE),
        id="research",
        name="Market Research",
        misfire_grace_time=300,
    )

    scheduler.add_job(
        run_hourly_check,
        CronTrigger.from_crontab(config.HOURLY_CRON, timezone=config.TIMEZONE),
        id="hourly_check",
        name="Hourly Market Check",
        misfire_grace_time=300,
    )

    scheduler.add_job(
        run_morning_report,
        CronTrigger.from_crontab(config.MORNING_REPORT_CRON, timezone=config.TIMEZONE),
        id="morning_report",
        name="Morning Report",
        misfire_grace_time=600,
    )

    scheduler.add_job(
        run_compaction,
        CronTrigger.from_crontab(config.COMPACTION_CRON, timezone=config.TIMEZONE),
        id="compaction",
        name="Memory Compaction",
        misfire_grace_time=600,
    )

    scheduler.add_job(
        run_sentiment,
        CronTrigger.from_crontab(config.SENTIMENT_CRON, timezone=config.TIMEZONE),
        id="sentiment",
        name="Sentiment Analysis",
        misfire_grace_time=300,
    )

    scheduler.add_job(
        run_risk_monitor,
        CronTrigger.from_crontab(config.RISK_MONITOR_CRON, timezone=config.TIMEZONE),
        id="risk_monitor",
        name="Risk Monitor",
        misfire_grace_time=60,
    )

    scheduler.add_job(
        run_rebalancer,
        CronTrigger.from_crontab(config.REBALANCER_CRON, timezone=config.TIMEZONE),
        id="rebalancer",
        name="Portfolio Rebalancer",
        misfire_grace_time=600,
    )

    scheduler.add_job(
        run_performance_analysis,
        CronTrigger.from_crontab(config.PERFORMANCE_CRON, timezone=config.TIMEZONE),
        id="performance",
        name="Performance Analysis",
        misfire_grace_time=600,
    )

    scheduler.add_job(
        run_events_calendar,
        CronTrigger.from_crontab(config.EVENTS_CRON, timezone=config.TIMEZONE),
        id="events",
        name="Events Calendar",
        misfire_grace_time=600,
    )

    scheduler.add_job(
        run_expansion_analysis,
        CronTrigger.from_crontab(config.EXPANSION_CRON, timezone=config.TIMEZONE),
        id="expansion",
        name="Portfolio Expansion",
        misfire_grace_time=600,
    )


def start_background_scheduler() -> BackgroundScheduler:
    """Start a non-blocking background scheduler (for use with FastAPI)."""
    global _bg_scheduler
    if _bg_scheduler and _bg_scheduler.running:
        return _bg_scheduler

    # Load user-approved instruments before scheduling any jobs
    load_approved_into_config()

    _bg_scheduler = BackgroundScheduler(timezone=config.TIMEZONE)
    _add_jobs(_bg_scheduler)
    _bg_scheduler.start()

    logger.info("Background scheduler started")
    logger.info(f"  Research: {config.RESEARCH_CRON}")
    logger.info(f"  Hourly check: {config.HOURLY_CRON}")
    logger.info(f"  Morning report: {config.MORNING_REPORT_CRON}")
    logger.info(f"  Compaction: {config.COMPACTION_CRON}")
    logger.info(f"  Sentiment: {config.SENTIMENT_CRON}")
    logger.info(f"  Risk monitor: {config.RISK_MONITOR_CRON}")
    logger.info(f"  Rebalancer: {config.REBALANCER_CRON}")
    logger.info(f"  Performance: {config.PERFORMANCE_CRON}")
    logger.info(f"  Events: {config.EVENTS_CRON}")
    logger.info(f"  Expansion: {config.EXPANSION_CRON}")
    return _bg_scheduler


def get_scheduler() -> BackgroundScheduler | None:
    return _bg_scheduler


def main():
    """Standalone blocking mode (for running without the API)."""
    logger.info("=" * 60)
    logger.info("Day Trader Agent Starting (standalone scheduler)")
    logger.info(f"Model: {config.TRADER_MODEL_NAME} @ {config.OLLAMA_BASE_URL}")
    logger.info(f"Timezone: {config.TIMEZONE}")
    logger.info(f"Research schedule: {config.RESEARCH_CRON}")
    logger.info(f"Hourly schedule: {config.HOURLY_CRON}")
    logger.info(f"Morning report schedule: {config.MORNING_REPORT_CRON}")
    logger.info(f"Compaction schedule: {config.COMPACTION_CRON}")
    logger.info(f"Sentiment schedule: {config.SENTIMENT_CRON}")
    logger.info(f"Risk monitor schedule: {config.RISK_MONITOR_CRON}")
    logger.info(f"Rebalancer schedule: {config.REBALANCER_CRON}")
    logger.info(f"Performance schedule: {config.PERFORMANCE_CRON}")
    logger.info(f"Events schedule: {config.EVENTS_CRON}")
    logger.info(f"Expansion schedule: {config.EXPANSION_CRON}")
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
