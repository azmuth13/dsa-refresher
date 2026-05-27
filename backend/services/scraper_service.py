from __future__ import annotations

import html
import logging
import re
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

SUPPORTED_DOMAINS = {
    "leetcode.com": "LeetCode",
    "codeforces.com": "Codeforces",
    "codechef.com": "CodeChef",
    "atcoder.jp": "AtCoder",
}

CP_ALGORITHMS_PATHS = {
    "arrays": "others/maximum_average_segment.html",
    "strings": "string/string-hashing.html",
    "string hashing": "string/string-hashing.html",
    "kmp": "string/prefix-function.html",
    "z-function": "string/z-function.html",
    "suffix array": "string/suffix-array.html",
    "sorting": "sequences/k-th.html",
    "binary search": "num_methods/binary_search.html",
    "ternary search": "num_methods/ternary_search.html",
    "dynamic programming": "dynamic_programming/intro-to-dp.html",
    "knapsack": "dynamic_programming/knapsack.html",
    "longest increasing subsequence": "sequences/longest_increasing_subsequence.html",
    "graphs": "graph/breadth-first-search.html",
    "breadth first search": "graph/breadth-first-search.html",
    "depth first search": "graph/depth-first-search.html",
    "dijkstra": "graph/dijkstra.html",
    "bellman ford": "graph/bellman_ford.html",
    "floyd warshall": "graph/all-pair-shortest-path-floyd-warshall.html",
    "minimum spanning tree": "graph/mst_kruskal.html",
    "topological sort": "graph/topological-sort.html",
    "strongly connected components": "graph/strongly-connected-components.html",
    "bridges": "graph/bridge-searching.html",
    "articulation points": "graph/cutpoints.html",
    "trees": "graph/lca.html",
    "lowest common ancestor": "graph/lca.html",
    "tree diameter": "graph/tree_painting.html",
    "binary lifting": "graph/lca_binary_lifting.html",
    "data structures": "data_structures/fenwick.html",
    "fenwick": "data_structures/fenwick.html",
    "segment tree": "data_structures/segment_tree.html",
    "disjoint set union": "data_structures/disjoint_set_union.html",
    "sparse table": "data_structures/sparse-table.html",
    "sqrt decomposition": "data_structures/sqrt_decomposition.html",
    "number theory": "algebra/prime-sieve-linear.html",
    "sieve": "algebra/sieve-of-eratosthenes.html",
    "gcd": "algebra/euclid-algorithm.html",
    "modular arithmetic": "algebra/module-inverse.html",
    "combinatorics": "combinatorics/binomial-coefficients.html",
    "geometry": "geometry/basic-geometry.html",
}


def _platform_from_url(url: str) -> str:
    domain = urlparse(url).netloc.lower().removeprefix("www.")
    for supported_domain, platform in SUPPORTED_DOMAINS.items():
        if domain == supported_domain or domain.endswith(f".{supported_domain}"):
            return platform
    return "Unknown"


def normalize_problem_url(url: str) -> str:
    parsed = urlparse(url.strip())
    domain = parsed.netloc.lower().removeprefix("www.")
    if domain == "codeforces.com":
        compact_match = re.fullmatch(r"/problemset/problem/(\d+)([A-Za-z]\d?)", parsed.path.rstrip("/"))
        if compact_match:
            contest_id, index = compact_match.groups()
            return f"{parsed.scheme or 'https'}://codeforces.com/problemset/problem/{contest_id}/{index.upper()}"
    return url.strip()


def _clean_text(value: str) -> str:
    value = re.sub(r"<(script|style).*?</\1>", " ", value, flags=re.DOTALL | re.IGNORECASE)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def _meta_content(page: str, property_name: str) -> str | None:
    patterns = [
        rf'<meta[^>]+property=["\']{re.escape(property_name)}["\'][^>]+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{re.escape(property_name)}["\']',
        rf'<meta[^>]+name=["\']{re.escape(property_name)}["\'][^>]+content=["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, page, flags=re.IGNORECASE)
        if match:
            return html.unescape(match.group(1)).strip()
    return None


def _title_from_html(page: str) -> str | None:
    og_title = _meta_content(page, "og:title")
    if og_title:
        return og_title
    match = re.search(r"<title[^>]*>(.*?)</title>", page, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return _clean_text(match.group(1))
    return None


def _extract_codeforces_tags(page: str) -> list[str]:
    tags = re.findall(r'<span[^>]*class=["\'][^"\']*tag-box[^"\']*["\'][^>]*>(.*?)</span>', page, re.DOTALL)
    return [_clean_text(tag) for tag in tags if _clean_text(tag)]


def _extract_codechef_tags(page: str) -> list[str]:
    tags = re.findall(r'<a[^>]+href=["\'][^"\']*/tags/problems/[^"\']+["\'][^>]*>(.*?)</a>', page, re.DOTALL)
    if not tags:
        tags = re.findall(r'"tags"\s*:\s*\[(.*?)\]', page, re.DOTALL)
        if tags:
            return re.findall(r'"name"\s*:\s*"([^"]+)"', tags[0])
    return [_clean_text(tag) for tag in tags if _clean_text(tag)]


async def parse_problem_metadata(url: str) -> dict:
    url = normalize_problem_url(url)
    platform = _platform_from_url(url)
    metadata = {"platform": platform, "title": url.rstrip("/").split("/")[-1], "url": url, "tags": []}

    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "DSA-Refresher/1.0"})
            response.raise_for_status()
            page = response.text
    except httpx.HTTPError as exc:
        logger.warning("Problem scrape failed for %s: %s", url, exc)
        return metadata

    try:
        title = _title_from_html(page) or metadata["title"]
        tags: list[str] = []

        if platform == "LeetCode":
            title = title.replace(" - LeetCode", "").strip()
        elif platform == "Codeforces":
            problem_statement_match = re.search(
                r'<div[^>]+class=["\']title["\'][^>]*>(.*?)</div>',
                page,
                flags=re.DOTALL | re.IGNORECASE,
            )
            if problem_statement_match:
                title = _clean_text(problem_statement_match.group(1))
            tags = _extract_codeforces_tags(page)
        elif platform == "CodeChef":
            title = title.replace("| CodeChef", "").replace("Practice", "").strip(" -")
            tags = _extract_codechef_tags(page)
        elif platform == "AtCoder":
            title = title.replace(" - AtCoder", "").strip()

        return {"platform": platform, "title": title, "url": url, "tags": tags[:8]}
    except Exception as exc:  # noqa: BLE001 - graceful fallback for brittle third-party HTML
        logger.warning("Problem metadata parse failed for %s: %s", url, exc)
        return metadata


def _path_for_topic(topic: str) -> str:
    normalized = topic.lower()
    for key, path in CP_ALGORITHMS_PATHS.items():
        if key in normalized:
            return path
    return "dynamic_programming/intro-to-dp.html"


async def fetch_cppalgorithms_context(topic: str) -> str:
    path = _path_for_topic(topic)
    url = f"https://cp-algorithms.com/{path}"
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "DSA-Refresher/1.0"})
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("cp-algorithms fetch failed for %s: %s", topic, exc)
        return ""

    page = response.text
    page = re.sub(r"<nav.*?</nav>|<footer.*?</footer>|<aside.*?</aside>", " ", page, flags=re.DOTALL | re.IGNORECASE)
    page = re.sub(r"<pre><code.*?</code></pre>", lambda m: "\n" + _clean_text(m.group(0)) + "\n", page, flags=re.DOTALL)
    text = _clean_text(page)
    return text[:2000]
