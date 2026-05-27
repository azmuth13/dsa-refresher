from __future__ import annotations

import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ValidationError

from config import get_settings
from services.llm_service import LLMService
from services.scraper_service import SUPPORTED_DOMAINS, normalize_problem_url, parse_problem_metadata
from services.supabase_service import (
    SupabaseError,
    delete_solved_problem,
    is_supabase_configured,
    list_solved_problems,
    unix_timestamp_to_iso,
    upsert_solved_problems,
)

router = APIRouter()


class ProblemUrl(BaseModel):
    url: str


class ProblemRefresher(BaseModel):
    problem_title: str
    platform: str
    url: str
    submissions_url: Optional[str] = None
    pattern_name: str
    pattern_intuition: str
    key_steps: list[str]
    gotchas: list[str]
    similar_problems: list[dict]
    revision_prompt: str
    model_used: Optional[str] = None
    fallback_used: bool = False
    fallback_reason: Optional[str] = None


class LeetCodeSubmission(BaseModel):
    title: str
    titleSlug: str
    timestamp: str
    statusDisplay: str
    lang: str


class LeetCodeSyncResponse(BaseModel):
    fetched: int
    accepted: int
    added: int
    total: int
    added_urls: list[str]


LEETCODE_TITLE_BY_SLUG: dict[str, str] = {}


SYSTEM_PROMPT = """You are a DSA pattern reinforcement coach. Given a competitive programming problem the user has previously solved, generate a refresher that reinforces the underlying pattern, not the solution itself.
Return only valid JSON with these exact fields:
{
  "problem_title": string,
  "platform": string,
  "url": string,
  "pattern_name": string,
  "pattern_intuition": string,
  "key_steps": [string],
  "gotchas": [string],
  "similar_problems": [{ "title": string, "url": string, "platform": string }],
  "revision_prompt": string
}"""


def _problems_path() -> Path:
    return Path(get_settings().PROBLEMS_FILE_PATH)


def _read_problem_urls() -> list[str]:
    path = _problems_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _file_problem_records() -> list[dict[str, Any]]:
    records = []
    for url in _read_problem_urls():
        slug = _leetcode_slug_from_url(url)
        if slug:
            records.append(
                {
                    "slug": slug,
                    "title": LEETCODE_TITLE_BY_SLUG.get(slug) or _title_from_slug(slug),
                    "url": _leetcode_problem_url(slug),
                    "submissions_url": leetcode_submissions_url_from_problem_url(url),
                    "source": "file",
                }
            )
        else:
            records.append({"url": url, "source": "file"})
    return records


def _supabase_row_from_problem_record(record: dict[str, Any]) -> Optional[dict[str, Any]]:
    slug = record.get("slug") or _leetcode_slug_from_url(record.get("url", ""))
    if not slug:
        return None

    return {
        "slug": slug,
        "title": record.get("title") or LEETCODE_TITLE_BY_SLUG.get(slug) or _title_from_slug(slug),
        "url": record.get("url") or _leetcode_problem_url(slug),
        "submissions_url": record.get("submissions_url") or f"https://leetcode.com/problems/{slug}/submissions/",
    }


def _leetcode_problem_url(slug: str) -> str:
    return f"https://leetcode.com/problems/{slug.strip('/')}/"


def _title_from_slug(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-") if part)


def _leetcode_slug_from_url(url: str) -> Optional[str]:
    parsed = urlparse(url)
    domain = parsed.netloc.lower().removeprefix("www.")
    if domain != "leetcode.com":
        return None

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or parts[0] != "problems":
        return None

    return parts[1]


def _leetcode_metadata_from_url(url: str) -> Optional[dict]:
    slug = _leetcode_slug_from_url(url)
    if not slug:
        return None

    return {
        "platform": "LeetCode",
        "title": LEETCODE_TITLE_BY_SLUG.get(slug) or _title_from_slug(slug),
        "url": _leetcode_problem_url(slug),
        "tags": [],
    }


def _metadata_from_problem_record(record: dict[str, Any]) -> Optional[dict]:
    url = record.get("url", "")
    slug = record.get("slug") or _leetcode_slug_from_url(url)
    if not slug:
        return None

    return {
        "platform": "LeetCode",
        "title": record.get("title") or LEETCODE_TITLE_BY_SLUG.get(slug) or _title_from_slug(slug),
        "url": record.get("url") or _leetcode_problem_url(slug),
        "tags": [],
    }


async def _read_problem_records() -> list[dict[str, Any]]:
    if not is_supabase_configured():
        return _file_problem_records()

    try:
        records = await list_solved_problems()
    except SupabaseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return records or _file_problem_records()


def leetcode_submissions_url_from_problem_url(url: str) -> Optional[str]:
    slug = _leetcode_slug_from_url(url)
    if not slug:
        return None

    return f"https://leetcode.com/problems/{slug}/submissions/"


def _existing_leetcode_slugs(urls: list[str]) -> set[str]:
    slugs = set()
    for url in urls:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().removeprefix("www.")
        parts = [part for part in parsed.path.split("/") if part]
        if domain == "leetcode.com" and len(parts) >= 2 and parts[0] == "problems":
            slugs.add(parts[1])
    return slugs


async def _fetch_leetcode_submissions() -> list[LeetCodeSubmission]:
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            response = await client.get(settings.LEETCODE_SUBMISSIONS_URL)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LeetCode submissions API returned {exc.response.status_code}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Could not fetch LeetCode submissions: {exc}") from exc

    payload = response.json()
    submissions = payload.get("submission", [])
    if not isinstance(submissions, list):
        raise HTTPException(status_code=502, detail="LeetCode submissions API returned an unexpected response")

    return [LeetCodeSubmission.model_validate(item) for item in submissions]


async def sync_leetcode_submissions_to_file() -> LeetCodeSyncResponse:
    submissions = await _fetch_leetcode_submissions()
    seen_in_response: set[str] = set()
    added_urls: list[str] = []
    accepted_rows_by_slug: dict[str, dict[str, Any]] = {}
    synced_at = datetime.now(timezone.utc).isoformat()

    for submission in submissions:
        slug = submission.titleSlug.strip()
        if submission.statusDisplay != "Accepted" or not slug:
            continue
        LEETCODE_TITLE_BY_SLUG[slug] = submission.title.strip() or _title_from_slug(slug)
        if slug in seen_in_response:
            continue

        seen_in_response.add(slug)
        accepted_rows_by_slug[slug] = {
            "slug": slug,
            "title": LEETCODE_TITLE_BY_SLUG[slug],
            "url": _leetcode_problem_url(slug),
            "submissions_url": f"https://leetcode.com/problems/{slug}/submissions/",
            "first_accepted_at": unix_timestamp_to_iso(submission.timestamp),
            "last_submission_at": unix_timestamp_to_iso(submission.timestamp),
            "last_synced_at": synced_at,
            "lang": submission.lang,
        }

    if is_supabase_configured():
        try:
            existing_records = await list_solved_problems()
            existing_by_slug = {record["slug"]: record for record in existing_records}
            rows_by_slug = {
                row["slug"]: row
                for row in (_supabase_row_from_problem_record(record) for record in _file_problem_records())
                if row
            }
            rows_by_slug.update(accepted_rows_by_slug)
            rows = []
            for slug, row in rows_by_slug.items():
                existing = existing_by_slug.get(slug)
                if not existing:
                    added_urls.append(row["url"])
                rows.append(
                    {
                        **row,
                        "first_accepted_at": existing.get("first_accepted_at") if existing else row.get("first_accepted_at"),
                        "last_synced_at": row.get("last_synced_at") or synced_at,
                    }
                )

            await upsert_solved_problems(rows)
            total = len(await list_solved_problems())
        except SupabaseError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        accepted_count = sum(1 for submission in submissions if submission.statusDisplay == "Accepted")
        return LeetCodeSyncResponse(
            fetched=len(submissions),
            accepted=accepted_count,
            added=len(added_urls),
            total=total,
            added_urls=added_urls,
        )

    existing_urls = _read_problem_urls()
    existing_slugs = _existing_leetcode_slugs(existing_urls)
    added_urls = [row["url"] for slug, row in accepted_rows_by_slug.items() if slug not in existing_slugs]

    if added_urls:
        path = _problems_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        prefix = "" if not path.exists() or not path.read_text(encoding="utf-8").strip() else "\n"
        with path.open("a", encoding="utf-8") as file:
            file.write(prefix + "\n".join(added_urls) + "\n")

    accepted_count = sum(1 for submission in submissions if submission.statusDisplay == "Accepted")
    return LeetCodeSyncResponse(
        fetched=len(submissions),
        accepted=accepted_count,
        added=len(added_urls),
        total=len(_read_problem_urls()),
        added_urls=added_urls,
    )


def _is_supported_url(url: str) -> bool:
    domain = urlparse(url).netloc.lower().removeprefix("www.")
    return any(domain == item or domain.endswith(f".{item}") for item in SUPPORTED_DOMAINS)


def _extract_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


async def _generate_refresher(metadata: dict, llm: LLMService) -> ProblemRefresher:
    user_prompt = json.dumps(
        {
            "problem_title": metadata["title"],
            "platform": metadata["platform"],
            "tags": metadata.get("tags", []),
            "url": metadata["url"],
            "instruction": "Infer the underlying DSA pattern and generate a concise refresher.",
        },
        indent=2,
    )
    raw = await llm.generate(SYSTEM_PROMPT, user_prompt)
    payload = _extract_json(raw)
    payload["model_used"] = llm.model_used
    payload["submissions_url"] = leetcode_submissions_url_from_problem_url(metadata["url"])
    return ProblemRefresher.model_validate(payload)


def _fallback_refresher(metadata: dict, llm: LLMService, reason: str) -> ProblemRefresher:
    tags = metadata.get("tags") or []
    pattern_name = tags[0].title() if tags else "General Problem-Solving Pattern"
    return ProblemRefresher(
        problem_title=metadata.get("title") or metadata.get("url", "Saved Problem"),
        platform=metadata.get("platform", "Unknown"),
        url=metadata.get("url", ""),
        submissions_url=leetcode_submissions_url_from_problem_url(metadata.get("url", "")),
        pattern_name=pattern_name,
        pattern_intuition=(
            "This fallback card was generated because the live LLM refresher failed for this item. "
            "Revisit the constraints, identify the main invariant, and reconstruct the approach from the solved problem."
        ),
        key_steps=[
            "Restate the input, output, and constraints before thinking about code.",
            "Identify whether the solved approach depends on ordering, graph traversal, dynamic programming, or a data structure invariant.",
            "Write the smallest state or invariant that explains why the approach works.",
            "Dry-run the approach on one edge case and one normal case.",
        ],
        gotchas=[
            "Do not memorize only the final code; recover the trigger that made the pattern useful.",
            "Check boundary cases such as empty ranges, single elements, disconnected components, or duplicate values.",
        ],
        similar_problems=[],
        revision_prompt="Mentally re-solve this problem from the constraints alone. Then compare your recovered invariant with your original solution.",
        model_used=llm.model_used,
        fallback_used=True,
        fallback_reason=reason,
    )


@router.get("/my-problems", response_model=list[ProblemRefresher])
async def my_problems(count: int = Query(default=1, ge=1, le=5)):
    problem_records = await _read_problem_records()
    if not problem_records:
        raise HTTPException(status_code=404, detail="No solved problems found")

    selected_records = random.sample(problem_records, k=min(count, len(problem_records)))
    llm = LLMService()
    refreshers: list[ProblemRefresher] = []
    for record in selected_records:
        metadata = _metadata_from_problem_record(record) or _leetcode_metadata_from_url(record["url"]) or await parse_problem_metadata(record["url"])
        try:
            refreshers.append(await _generate_refresher(metadata, llm))
        except (json.JSONDecodeError, ValidationError):
            strict_prompt = (
                SYSTEM_PROMPT
                + "\nYour previous response failed JSON validation. Return only one complete JSON object. Escape newlines in strings and do not truncate strings."
            )
            raw = await llm.generate(strict_prompt, json.dumps(metadata, indent=2))
            try:
                payload = _extract_json(raw)
                payload["model_used"] = llm.model_used
                payload["submissions_url"] = leetcode_submissions_url_from_problem_url(metadata["url"])
                refreshers.append(ProblemRefresher.model_validate(payload))
            except (json.JSONDecodeError, ValidationError) as exc:
                refreshers.append(_fallback_refresher(metadata, llm, f"Invalid LLM JSON: {exc}"))
        except HTTPException as exc:
            refreshers.append(_fallback_refresher(metadata, llm, str(exc.detail)))
    return refreshers


@router.get("/problems/list")
async def list_problems():
    records = await _read_problem_records()
    problems = [record["url"] for record in records]
    return {
        "source": "supabase" if is_supabase_configured() else "file",
        "total": len(problems),
        "problems": problems,
    }


@router.post("/problems/sync-leetcode", response_model=LeetCodeSyncResponse)
async def sync_leetcode_problems():
    return await sync_leetcode_submissions_to_file()


@router.post("/problems/add")
async def add_problem(body: ProblemUrl):
    normalized_url = normalize_problem_url(body.url)
    if not _is_supported_url(normalized_url):
        raise HTTPException(status_code=400, detail="Unsupported problem URL domain")

    slug = _leetcode_slug_from_url(normalized_url)
    if is_supabase_configured() and slug:
        row = {
            "slug": slug,
            "title": LEETCODE_TITLE_BY_SLUG.get(slug) or _title_from_slug(slug),
            "url": _leetcode_problem_url(slug),
            "submissions_url": f"https://leetcode.com/problems/{slug}/submissions/",
        }
        try:
            await upsert_solved_problems([row])
            total = len(await list_solved_problems())
        except SupabaseError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {"total": total, "url": row["url"]}

    path = _problems_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = _read_problem_urls()
    if normalized_url not in existing:
        with path.open("a", encoding="utf-8") as file:
            file.write(f"\n{normalized_url}\n")
    return {"total": len(_read_problem_urls()), "url": normalized_url}


@router.delete("/problems/remove")
async def remove_problem(body: ProblemUrl):
    normalized_url = normalize_problem_url(body.url)
    slug = _leetcode_slug_from_url(normalized_url)
    if is_supabase_configured() and slug:
        try:
            removed = await delete_solved_problem(slug)
            total = len(await list_solved_problems())
        except SupabaseError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {"total": total, "removed": removed}

    path = _problems_path()
    if not path.exists():
        return {"total": 0, "removed": False}

    lines = path.read_text(encoding="utf-8").splitlines()
    removed = False
    kept_lines = []
    for line in lines:
        if normalize_problem_url(line.strip()) == normalized_url:
            removed = True
            continue
        kept_lines.append(line)
    path.write_text("\n".join(kept_lines) + "\n", encoding="utf-8")
    return {"total": len(_read_problem_urls()), "removed": removed}
