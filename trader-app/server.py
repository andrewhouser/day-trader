"""Server entry point: FastAPI app + background scheduler."""
import logging
from contextlib import asynccontextmanager

from api import app
from scheduler import start_background_scheduler, get_scheduler
from expansion import load_approved_into_config

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application):
    """Start scheduler on startup, shut down on exit."""
    logger.info("Loading user-approved instruments...")
    load_approved_into_config()
    logger.info("Starting background scheduler alongside API...")
    scheduler = start_background_scheduler()
    yield
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")


app.router.lifespan_context = lifespan
