from __future__ import annotations

import html
import json
import logging
import random
import re
from functools import lru_cache
from pathlib import Path

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

CP_BLOGS_PATH = Path(__file__).resolve().parent.parent / "data" / "cp_blogs.json"


@lru_cache
def load_cp_blogs() -> dict:
    if not CP_BLOGS_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="CPBites knowledge base is missing. Run backend/scripts/scrape_codeforces_blogs.py first.",
        )
    return json.loads(CP_BLOGS_PATH.read_text(encoding="utf-8"))


def list_cp_blogs() -> list[dict]:
    return load_cp_blogs().get("articles", [])


def get_random_cp_article(category: str | None = None) -> dict:
    articles = list_cp_blogs()
    if category:
        normalized = category.lower()
        articles = [article for article in articles if normalized in article.get("category", "").lower()]
    if not articles:
        raise HTTPException(status_code=404, detail="No CPBites articles found for that filter")
    return random.choice(articles)


def _clean_html_text(page: str) -> str:
    page = re.sub(r"<(script|style).*?</\1>", " ", page, flags=re.DOTALL | re.IGNORECASE)
    page = re.sub(r"<pre><code.*?</code></pre>", lambda m: "\n" + _strip_tags(m.group(0)) + "\n", page, flags=re.DOTALL)
    return _strip_tags(page)


def _strip_tags(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


async def fetch_codeforces_article_excerpt(url: str, max_chars: int = 3000) -> str:
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "DSA-Refresher/1.0"})
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Codeforces article fetch failed for %s: %s", url, exc)
        return ""

    text = _clean_html_text(response.text)
    return text[:max_chars]
