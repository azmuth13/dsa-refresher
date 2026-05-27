from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from config import get_settings


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
        "select": "slug,title,url,submissions_url,first_accepted_at,last_submission_at,last_synced_at,lang",
        "order": "last_submission_at.desc.nullslast,created_at.desc",
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(_table_url(), headers=_headers(), params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        raise SupabaseError(f"Supabase list failed: {exc.response.text}") from exc
    except httpx.HTTPError as exc:
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
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                _table_url(),
                headers=_headers("resolution=merge-duplicates,return=representation"),
                params=params,
                json=normalized_rows,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        raise SupabaseError(f"Supabase upsert failed: {exc.response.text}") from exc
    except httpx.HTTPError as exc:
        raise SupabaseError(f"Could not reach Supabase: {exc}") from exc


async def delete_solved_problem(slug: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.delete(
                _table_url(),
                headers=_headers("return=representation"),
                params={"slug": f"eq.{slug}"},
            )
            response.raise_for_status()
            return bool(response.json())
    except httpx.HTTPStatusError as exc:
        raise SupabaseError(f"Supabase delete failed: {exc.response.text}") from exc
    except httpx.HTTPError as exc:
        raise SupabaseError(f"Could not reach Supabase: {exc}") from exc
