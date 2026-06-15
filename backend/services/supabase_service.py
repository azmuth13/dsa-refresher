from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from config import get_settings

logger = logging.getLogger(__name__)


class SupabaseNotConfiguredError(RuntimeError):
    pass


class SupabaseError(RuntimeError):
    pass


def is_supabase_configured() -> bool:
    settings = get_settings()
    return bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY)


def _table_url() -> str:
    settings = get_settings()
    if not is_supabase_configured():
        raise SupabaseNotConfiguredError("Supabase URL or service role key is missing")

    base_url = settings.SUPABASE_URL.rstrip("/")
    return f"{base_url}/rest/v1/{settings.SUPABASE_SOLVED_PROBLEMS_TABLE}"


def _headers(prefer: Optional[str] = None) -> dict[str, str]:
    settings = get_settings()
    headers = {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def unix_timestamp_to_iso(timestamp: str | int | None) -> Optional[str]:
    if timestamp is None:
        return None
    try:
        value = int(timestamp)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


async def list_solved_problems() -> list[dict[str, Any]]:
    params = {
        "select": (
            "slug,title,url,submissions_url,first_accepted_at,last_submission_at,last_synced_at,lang,"
            "created_at,is_daily_bite_pointer,daily_bite_last_shown_at"
        ),
        "order": "created_at.asc",
    }
    logger.debug("Supabase list_solved_problems called")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(_table_url(), headers=_headers(), params=params)
            response.raise_for_status()
            records = response.json()
            logger.debug("Supabase list_solved_problems succeeded", extra={"count": len(records)})
            return records
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Supabase list failed with HTTP error",
            extra={"status_code": exc.response.status_code, "response_body": exc.response.text[:500]},
            exc_info=True,
        )
        raise SupabaseError(f"Supabase list failed: {exc.response.text}") from exc
    except httpx.HTTPError as exc:
        logger.error("Supabase list failed — cannot reach Supabase", exc_info=True)
        raise SupabaseError(f"Could not reach Supabase: {exc}") from exc


async def advance_daily_bite_pointer(shown_slug: str, next_slug: str, shown_at: str) -> None:
    logger.debug(
        "Supabase advance_daily_bite_pointer called",
        extra={"shown_slug": shown_slug, "next_slug": next_slug},
    )
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            clear_response = await client.patch(
                _table_url(),
                headers=_headers(),
                params={"is_daily_bite_pointer": "eq.true"},
                json={"is_daily_bite_pointer": False},
            )
            clear_response.raise_for_status()

            shown_response = await client.patch(
                _table_url(),
                headers=_headers(),
                params={"slug": f"eq.{shown_slug}"},
                json={"daily_bite_last_shown_at": shown_at},
            )
            shown_response.raise_for_status()

            mark_response = await client.patch(
                _table_url(),
                headers=_headers("return=representation"),
                params={"slug": f"eq.{next_slug}"},
                json={"is_daily_bite_pointer": True},
            )
            mark_response.raise_for_status()
            logger.info(
                "Supabase daily bite pointer advanced",
                extra={"shown_slug": shown_slug, "next_slug": next_slug},
            )
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Supabase daily bite pointer update failed with HTTP error",
            extra={
                "shown_slug": shown_slug,
                "next_slug": next_slug,
                "status_code": exc.response.status_code,
                "response_body": exc.response.text[:500],
            },
            exc_info=True,
        )
        raise SupabaseError(f"Supabase daily bite pointer update failed: {exc.response.text}") from exc
    except httpx.HTTPError as exc:
        logger.error(
            "Supabase daily bite pointer update failed — cannot reach Supabase",
            extra={"shown_slug": shown_slug, "next_slug": next_slug},
            exc_info=True,
        )
        raise SupabaseError(f"Could not reach Supabase: {exc}") from exc


async def upsert_solved_problems(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []

    columns = {
        "slug",
        "title",
        "url",
        "submissions_url",
        "first_accepted_at",
        "last_submission_at",
        "last_synced_at",
        "lang",
    }
    normalized_rows = [{column: row.get(column) for column in columns} for row in rows]

    params = {"on_conflict": "slug"}
    logger.debug("Supabase upsert_solved_problems called", extra={"row_count": len(normalized_rows)})
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                _table_url(),
                headers=_headers("resolution=merge-duplicates,return=representation"),
                params=params,
                json=normalized_rows,
            )
            response.raise_for_status()
            result = response.json()
            logger.info(
                "Supabase upsert succeeded",
                extra={"upserted_count": len(normalized_rows)},
            )
            return result
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Supabase upsert failed with HTTP error",
            extra={"status_code": exc.response.status_code, "response_body": exc.response.text[:500]},
            exc_info=True,
        )
        raise SupabaseError(f"Supabase upsert failed: {exc.response.text}") from exc
    except httpx.HTTPError as exc:
        logger.error("Supabase upsert failed — cannot reach Supabase", exc_info=True)
        raise SupabaseError(f"Could not reach Supabase: {exc}") from exc


async def delete_solved_problem(slug: str) -> bool:
    logger.debug("Supabase delete_solved_problem called", extra={"slug": slug})
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.delete(
                _table_url(),
                headers=_headers("return=representation"),
                params={"slug": f"eq.{slug}"},
            )
            response.raise_for_status()
            deleted = bool(response.json())
            logger.info("Supabase delete succeeded", extra={"slug": slug, "deleted": deleted})
            return deleted
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Supabase delete failed with HTTP error",
            extra={"slug": slug, "status_code": exc.response.status_code, "response_body": exc.response.text[:500]},
            exc_info=True,
        )
        raise SupabaseError(f"Supabase delete failed: {exc.response.text}") from exc
    except httpx.HTTPError as exc:
        logger.error("Supabase delete failed — cannot reach Supabase", extra={"slug": slug}, exc_info=True)
        raise SupabaseError(f"Could not reach Supabase: {exc}") from exc
