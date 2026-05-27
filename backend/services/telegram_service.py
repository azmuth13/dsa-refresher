from __future__ import annotations

from html import escape
from typing import Any

import httpx

from config import get_settings


class TelegramNotConfiguredError(RuntimeError):
    pass


class TelegramSendError(RuntimeError):
    pass


def _clean_items(items: list[str] | None, limit: int = 3) -> list[str]:
    if not items:
        return []
    return [item.strip() for item in items[:limit] if item and item.strip()]


def _as_dict(payload: Any) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    if isinstance(payload, dict):
        return payload
    return dict(payload)


async def send_telegram_message(message: str) -> None:
    settings = get_settings()
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        raise TelegramNotConfiguredError("Telegram bot token or chat id is missing")

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": settings.TELEGRAM_PARSE_MODE,
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        raise TelegramSendError(f"Telegram API rejected the message: {detail}") from exc
    except httpx.HTTPError as exc:
        raise TelegramSendError(f"Could not reach Telegram: {exc}") from exc


def format_dsa_bite_message(bite: Any) -> str:
    data = _as_dict(bite)
    lines = [
        "<b>Today's DSABite</b>",
        "",
        f"<b>{escape(data.get('topic_name', 'Random Topic'))}</b>",
        f"Category: {escape(data.get('category', 'N/A'))}",
        f"Difficulty: {escape(data.get('difficulty', 'N/A'))}",
        "",
        f"<b>Core concept</b>: {escape(data.get('core_concept', 'N/A'))}",
        f"<b>Key insight</b>: {escape(data.get('key_insight', 'N/A'))}",
    ]

    pitfalls = _clean_items(data.get("common_pitfalls"))
    if pitfalls:
        lines.extend(["", "<b>Watch out for</b>:"])
        lines.extend(f"- {escape(item)}" for item in pitfalls)

    example_problem = data.get("example_problem") or {}
    if example_problem.get("title"):
        lines.extend(
            [
                "",
                f"<b>Practice prompt</b>: {escape(example_problem['title'])}",
                escape(example_problem.get("approach", "")),
            ]
        )

    practice_links = data.get("practice_links") or []
    if practice_links:
        first_link = practice_links[0]
        title = escape(first_link.get("title", "Practice link"))
        url = escape(first_link.get("url", ""))
        lines.extend(["", f"<a href=\"{url}\">{title}</a>"])

    return "\n".join(line for line in lines if line is not None)


def format_cp_bite_message(bite: Any) -> str:
    data = _as_dict(bite)
    lines = [
        "<b>Today's CPBite</b>",
        "",
        f"<b>{escape(data.get('article_title', 'Codeforces Article'))}</b>",
        f"Category: {escape(data.get('category', 'N/A'))}",
        "",
        f"<b>Core idea</b>: {escape(data.get('core_idea', 'N/A'))}",
        f"<b>Why it matters</b>: {escape(data.get('why_it_matters', 'N/A'))}",
    ]

    takeaways = _clean_items(data.get("key_takeaways"))
    if takeaways:
        lines.extend(["", "<b>Key takeaways</b>:"])
        lines.extend(f"- {escape(item)}" for item in takeaways)

    if data.get("practice_angle"):
        lines.extend(["", f"<b>Practice angle</b>: {escape(data['practice_angle'])}"])

    if data.get("source_url"):
        url = escape(data["source_url"])
        lines.extend(["", f"<a href=\"{url}\">Read source</a>"])

    return "\n".join(line for line in lines if line is not None)


def format_my_problem_bite_message(bite: Any) -> str:
    data = _as_dict(bite)
    lines = [
        "<b>Today's My Problem Bite</b>",
        "",
        f"<b>{escape(data.get('problem_title', 'Saved Problem'))}</b>",
        f"Platform: {escape(data.get('platform', 'N/A'))}",
        "",
        f"<b>Pattern</b>: {escape(data.get('pattern_name', 'N/A'))}",
        f"<b>Intuition</b>: {escape(data.get('pattern_intuition', 'N/A'))}",
    ]

    steps = _clean_items(data.get("key_steps"))
    if steps:
        lines.extend(["", "<b>Key steps</b>:"])
        lines.extend(f"- {escape(item)}" for item in steps)

    gotchas = _clean_items(data.get("gotchas"), limit=2)
    if gotchas:
        lines.extend(["", "<b>Gotchas</b>:"])
        lines.extend(f"- {escape(item)}" for item in gotchas)

    if data.get("revision_prompt"):
        lines.extend(["", f"<b>Revision prompt</b>: {escape(data['revision_prompt'])}"])

    if data.get("submissions_url"):
        url = escape(data["submissions_url"])
        lines.extend(["", f"<a href=\"{url}\">Open LeetCode submissions</a>"])
    elif data.get("url"):
        url = escape(data["url"])
        lines.extend(["", f"<a href=\"{url}\">Open problem</a>"])

    return "\n".join(line for line in lines if line is not None)
