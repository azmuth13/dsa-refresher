from __future__ import annotations

import json
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, ValidationError

from services.cp_bites_service import fetch_codeforces_article_excerpt, get_random_cp_article, load_cp_blogs
from services.llm_service import LLMService

router = APIRouter()


class CPBiteResponse(BaseModel):
    article_title: str
    category: str
    source_url: str
    source_index_url: str
    core_idea: str
    why_it_matters: str
    when_to_use: list[str]
    key_takeaways: list[str]
    mental_model: str
    practice_angle: str
    source_excerpt_used: bool = Field(default=False)
    model_used: str


SYSTEM_PROMPT = """You are CPBites, a concise competitive-programming study coach.
You must generate a bite strictly from the supplied Codeforces blog article metadata and excerpt.
Do not introduce external sources, external article links, or unrelated topics.
Return only valid JSON with these exact fields:
{
  "article_title": string,
  "category": string,
  "source_url": string,
  "source_index_url": string,
  "core_idea": string,
  "why_it_matters": string,
  "when_to_use": [string],
  "key_takeaways": [string],
  "mental_model": string,
  "practice_angle": string
}"""


def _extract_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


async def _generate_and_validate(llm: LLMService, article: dict, excerpt: str) -> CPBiteResponse:
    user_prompt = json.dumps(
        {
            "article": article,
            "source_excerpt": excerpt or "No article excerpt could be fetched. Use only the article title, category, and URL metadata.",
            "instruction": "Create one compact CPBite. Stay strictly grounded in this selected Codeforces article.",
        },
        indent=2,
    )
    raw = await llm.generate(SYSTEM_PROMPT, user_prompt)
    payload = _extract_json(raw)
    payload["source_excerpt_used"] = bool(excerpt)
    payload["model_used"] = llm.model_used
    return CPBiteResponse.model_validate(payload)


@router.get("/cp-bites", response_model=CPBiteResponse)
async def cp_bites(category: Optional[str] = Query(default=None)):
    article = get_random_cp_article(category)
    excerpt = await fetch_codeforces_article_excerpt(article["url"])
    llm = LLMService()

    try:
        return await _generate_and_validate(llm, article, excerpt)
    except (json.JSONDecodeError, ValidationError):
        strict_prompt = (
            SYSTEM_PROMPT
            + "\nYour previous response failed JSON validation. Return one complete JSON object only. Escape newlines in strings."
        )
        raw = await llm.generate(
            strict_prompt,
            json.dumps({"article": article, "source_excerpt": excerpt}, indent=2),
        )
        try:
            payload = _extract_json(raw)
            payload["source_excerpt_used"] = bool(excerpt)
            payload["model_used"] = llm.model_used
            return CPBiteResponse.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise HTTPException(status_code=502, detail=f"LLM returned invalid CPBite JSON: {exc}") from exc


@router.get("/cp-bites/sources")
async def cp_bites_sources():
    data = load_cp_blogs()
    return {
        "source_url": data.get("source_url"),
        "total": data.get("total", 0),
        "articles": data.get("articles", []),
    }
