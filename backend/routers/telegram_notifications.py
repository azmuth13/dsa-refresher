from __future__ import annotations

import logging
from typing import Any, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from routers.cp_bites import CPBiteResponse, cp_bites
from routers.my_problems import ProblemRefresher, my_problems
from routers.random_topic import RandomTopicResponse, random_topic
from services.daily_my_problem_scheduler import run_daily_my_problem_telegram_job
from services.telegram_service import (
    TelegramNotConfiguredError,
    TelegramSendError,
    format_cp_bite_message,
    format_dsa_bite_message,
    format_my_problem_bite_message,
    send_telegram_message,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


class TelegramMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=3500)


class CPBiteTelegramRequest(BaseModel):
    category: Optional[str] = None


class TelegramSendResponse(BaseModel):
    status: str
    message: str


class ExistingBiteTelegramRequest(BaseModel):
    mode: Literal["random", "cpbites", "myproblems"]
    bite: Any


async def _send_or_raise(message: str) -> None:
    try:
        await send_telegram_message(message)
    except TelegramNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TelegramSendError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


async def _generate_and_send_dsa_bite() -> RandomTopicResponse:
    bite = await random_topic()
    await send_telegram_message(format_dsa_bite_message(bite))
    logger.info("DSA bite sent to Telegram", extra={"topic": bite.topic_name})
    return bite


async def _generate_and_send_cp_bite(category: Optional[str] = None) -> CPBiteResponse:
    bite = await cp_bites(category=category)
    await send_telegram_message(format_cp_bite_message(bite))
    logger.info("CP bite sent to Telegram", extra={"article_title": bite.article_title, "category": bite.category})
    return bite


async def _generate_and_send_my_problem_bite() -> ProblemRefresher:
    bites = await my_problems(count=1)
    bite = bites[0]
    await send_telegram_message(format_my_problem_bite_message(bite))
    logger.info("My Problem bite sent to Telegram", extra={"problem_title": bite.problem_title})
    return bite


async def _generate_and_send_dsa_bite_safe() -> None:
    """Background-task wrapper that logs failures instead of silently dropping them."""
    try:
        await _generate_and_send_dsa_bite()
    except Exception:
        logger.exception("Background DSA bite task failed")


async def _generate_and_send_cp_bite_safe(category: Optional[str] = None) -> None:
    """Background-task wrapper that logs failures instead of silently dropping them."""
    try:
        await _generate_and_send_cp_bite(category=category)
    except Exception:
        logger.exception("Background CP bite task failed", extra={"category": category})


async def _generate_and_send_my_problem_bite_safe() -> None:
    """Background-task wrapper that logs failures instead of silently dropping them."""
    try:
        await _generate_and_send_my_problem_bite()
    except Exception:
        logger.exception("Background My Problem bite task failed")


@router.post("/notify", response_model=TelegramSendResponse)
async def notify_telegram(request: TelegramMessageRequest):
    await _send_or_raise(request.message)
    return {"status": "sent", "message": "Telegram notification sent"}


@router.post("/send-existing-bite", response_model=TelegramSendResponse)
async def send_existing_bite_to_telegram(request: ExistingBiteTelegramRequest):
    bite = request.bite[0] if request.mode == "myproblems" and isinstance(request.bite, list) else request.bite
    if not bite:
        raise HTTPException(status_code=400, detail="No bite payload provided")

    if request.mode == "random":
        message = format_dsa_bite_message(bite)
    elif request.mode == "cpbites":
        message = format_cp_bite_message(bite)
    else:
        message = format_my_problem_bite_message(bite)

    await _send_or_raise(message)
    return {"status": "sent", "message": "Current bite sent to Telegram"}


@router.post("/dsa-bite")
async def send_dsa_bite_to_telegram():
    try:
        bite = await _generate_and_send_dsa_bite()
    except TelegramNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TelegramSendError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"status": "sent", "message": "DSABite sent to Telegram", "bite": bite}


@router.post("/cp-bite")
async def send_cp_bite_to_telegram(request: Optional[CPBiteTelegramRequest] = None):
    try:
        bite = await _generate_and_send_cp_bite(category=request.category if request else None)
    except TelegramNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TelegramSendError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"status": "sent", "message": "CPBite sent to Telegram", "bite": bite}


@router.post("/my-problem")
async def send_my_problem_bite_to_telegram():
    try:
        bite = await _generate_and_send_my_problem_bite()
    except TelegramNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TelegramSendError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"status": "sent", "message": "My Problem bite sent to Telegram", "bite": bite}


@router.post("/daily-my-problem/run")
async def run_daily_my_problem_bite_now():
    try:
        return await run_daily_my_problem_telegram_job()
    except TelegramNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TelegramSendError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/dsa-bite-bg", response_model=TelegramSendResponse)
async def queue_dsa_bite_for_telegram(background_tasks: BackgroundTasks):
    background_tasks.add_task(_generate_and_send_dsa_bite_safe)
    logger.info("DSA bite background task queued")
    return {"status": "queued", "message": "DSABite will be generated and sent to Telegram"}


@router.post("/cp-bite-bg", response_model=TelegramSendResponse)
async def queue_cp_bite_for_telegram(
    background_tasks: BackgroundTasks,
    request: Optional[CPBiteTelegramRequest] = None,
):
    background_tasks.add_task(_generate_and_send_cp_bite_safe, request.category if request else None)
    logger.info("CP bite background task queued", extra={"category": request.category if request else None})
    return {"status": "queued", "message": "CPBite will be generated and sent to Telegram"}


@router.post("/my-problem-bg", response_model=TelegramSendResponse)
async def queue_my_problem_bite_for_telegram(background_tasks: BackgroundTasks):
    background_tasks.add_task(_generate_and_send_my_problem_bite_safe)
    logger.info("My Problem bite background task queued")
    return {"status": "queued", "message": "My Problem bite will be generated and sent to Telegram"}
