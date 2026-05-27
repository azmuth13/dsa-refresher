from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from config import get_settings
from routers.my_problems import ProblemRefresher, my_problems, sync_leetcode_submissions_to_file
from services.telegram_service import format_my_problem_bite_message, send_telegram_message

logger = logging.getLogger(__name__)


def _parse_hhmm(value: str) -> time:
    try:
        hour_text, minute_text = value.split(":", maxsplit=1)
        hour = int(hour_text)
        minute = int(minute_text)
    except ValueError as exc:
        raise ValueError("Daily Telegram time must be in HH:MM format") from exc

    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("Daily Telegram time must be a valid 24-hour HH:MM value")

    return time(hour=hour, minute=minute)


def _timezone() -> ZoneInfo:
    settings = get_settings()
    try:
        return ZoneInfo(settings.DAILY_MY_PROBLEM_TELEGRAM_TIMEZONE)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown timezone: {settings.DAILY_MY_PROBLEM_TELEGRAM_TIMEZONE}") from exc


def next_daily_run(now: Optional[datetime] = None) -> datetime:
    settings = get_settings()
    tz = _timezone()
    current = now.astimezone(tz) if now else datetime.now(tz)
    scheduled_time = _parse_hhmm(settings.DAILY_MY_PROBLEM_TELEGRAM_TIME)
    scheduled = datetime.combine(current.date(), scheduled_time, tzinfo=tz)

    if scheduled <= current:
        scheduled += timedelta(days=1)

    return scheduled


async def run_daily_my_problem_telegram_job() -> dict:
    sync_result = await sync_leetcode_submissions_to_file()
    bites = await my_problems(count=1)
    bite: ProblemRefresher = bites[0]
    await send_telegram_message(format_my_problem_bite_message(bite))

    return {
        "status": "sent",
        "message": "Daily My Problem bite sent to Telegram",
        "sync": sync_result.model_dump(),
        "bite": bite.model_dump(),
    }


class DailyMyProblemTelegramScheduler:
    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        settings = get_settings()
        if not settings.DAILY_MY_PROBLEM_TELEGRAM_ENABLED:
            logger.info("Daily My Problem Telegram scheduler is disabled")
            return

        if self._task and not self._task.done():
            return

        self._task = asyncio.create_task(self._run_forever())

    async def stop(self) -> None:
        if not self._task:
            return

        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None

    async def _run_forever(self) -> None:
        while True:
            run_at = next_daily_run()
            sleep_for = max(0, (run_at - datetime.now(run_at.tzinfo)).total_seconds())
            logger.info("Next daily My Problem Telegram job scheduled for %s", run_at.isoformat())

            try:
                await asyncio.sleep(sleep_for)
                logger.info("Starting daily My Problem Telegram job")
                result = await run_daily_my_problem_telegram_job()
                logger.info(
                    "Daily My Problem Telegram job completed: added=%s total=%s title=%s",
                    result["sync"]["added"],
                    result["sync"]["total"],
                    result["bite"]["problem_title"],
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Daily My Problem Telegram job failed")


daily_my_problem_telegram_scheduler = DailyMyProblemTelegramScheduler()
