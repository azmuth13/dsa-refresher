"""Standalone cron entry-point for the daily My Problem Telegram bite.

Render spins this up on schedule, runs the job, and tears it down.
No dependency on the web service being awake.

Usage (local test):
    python scripts/cron_daily_bite.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure the backend package root is on sys.path so imports work
# when Render runs this from the backend/ directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from logging_config import setup_logging  # noqa: E402
from config import get_settings  # noqa: E402

settings = get_settings()
setup_logging(settings.LOG_LEVEL)

import logging  # noqa: E402

logger = logging.getLogger(__name__)


async def main() -> None:
    from services.daily_my_problem_scheduler import run_daily_my_problem_telegram_job

    logger.info("Cron job started: daily My Problem Telegram bite")
    try:
        result = await run_daily_my_problem_telegram_job()
        logger.info(
            "Cron job completed successfully",
            extra={
                "added": result["sync"]["added"],
                "total": result["sync"]["total"],
                "problem_title": result["bite"]["problem_title"],
            },
        )
    except Exception:
        logger.exception("Cron job failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
