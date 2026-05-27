from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

import httpx

SOURCE_URL = "https://codeforces.com/blog/entry/91363"
BASE_URL = "https://codeforces.com"
DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "data" / "cp_blogs.json"


class CodeforcesBlogIndexParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current_heading: str | None = None
        self.capture_heading: str | None = None
        self.capture_link: dict | None = None
        self.heading_text: list[str] = []
        self.link_text: list[str] = []
        self.entries: list[dict] = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag in {"h1", "h2"}:
            self.capture_heading = tag
            self.heading_text = []
        if tag == "a" and self.current_heading:
            href = attrs_dict.get("href", "")
            if "/blog/entry/" in href:
                self.capture_link = {"href": urljoin(BASE_URL, href)}
                self.link_text = []

    def handle_data(self, data):
        if self.capture_heading:
            self.heading_text.append(data)
        if self.capture_link is not None:
            self.link_text.append(data)

    def handle_endtag(self, tag):
        if self.capture_heading == tag:
            heading = _clean_text(" ".join(self.heading_text))
            if heading and not heading.lower().startswith("comments"):
                self.current_heading = heading
            self.capture_heading = None
            self.heading_text = []

        if tag == "a" and self.capture_link is not None:
            title = _clean_text(" ".join(self.link_text))
            href = self.capture_link["href"]
            if title and href != SOURCE_URL:
                self.entries.append(
                    {
                        "id": _entry_id(href),
                        "title": title,
                        "category": self.current_heading,
                        "url": href,
                        "source_index_url": SOURCE_URL,
                    }
                )
            self.capture_link = None
            self.link_text = []


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _entry_id(url: str) -> str:
    match = re.search(r"/blog/entry/(\d+)", url)
    if match:
        return f"cf_blog_{match.group(1)}"
    slug = re.sub(r"[^a-z0-9]+", "_", url.lower()).strip("_")
    return f"cf_blog_{slug}"


async def scrape_index() -> list[dict]:
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        response = await client.get(SOURCE_URL, headers={"User-Agent": "DSA-Refresher/1.0"})
        response.raise_for_status()

    parser = CodeforcesBlogIndexParser()
    parser.feed(response.text)

    deduped: dict[str, dict] = {}
    for entry in parser.entries:
        deduped.setdefault(entry["url"], entry)

    return sorted(deduped.values(), key=lambda item: (item["category"] or "", item["title"].lower()))


async def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape the Codeforces useful blogs index into local JSON.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    entries = await scrape_index()
    payload = {
        "source_url": SOURCE_URL,
        "description": "Local index of Codeforces blog articles listed in the useful blogs master post. Full articles are fetched on demand.",
        "total": len(entries),
        "articles": entries,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(entries)} Codeforces blog links to {args.output}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
