from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

WMN_URL = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131 Safari/537.36 TraceFox/0.1"
)

FALLBACK_SITES = [
    {
        "name": "GitHub",
        "uri_check": "https://github.com/{account}",
        "uri_pretty": "https://github.com/{account}",
        "e_code": 200,
        "e_string": "itemprop=\"additionalName\"",
        "m_code": 404,
        "m_string": "",
        "cat": "coding",
        "valid": True,
    },
    {
        "name": "Reddit",
        "uri_check": "https://www.reddit.com/user/{account}/about.json",
        "uri_pretty": "https://www.reddit.com/user/{account}",
        "e_code": 200,
        "e_string": "\"name\"",
        "m_code": 404,
        "m_string": "",
        "cat": "social",
        "valid": True,
    },
]


@dataclass(slots=True)
class ScanConfig:
    timeout: float = 12.0
    concurrency: int = 30
    max_sites: int | None = None


def normalize_username(username: str) -> str:
    value = username.strip().lstrip("@").strip()
    if not value:
        raise ValueError("Username cannot be empty")
    if len(value) > 80:
        raise ValueError("Username is too long")
    if any(ch in value for ch in "\r\n\t"):
        raise ValueError("Username contains invalid whitespace")
    return value


def _format_template(value: str, username: str) -> str:
    encoded = quote(username, safe="._-")
    return value.replace("{account}", encoded).replace("{}", encoded)


def classify_response(site: dict[str, Any], status: int, text: str) -> str:
    e_code = int(site.get("e_code", 200))
    m_code = int(site.get("m_code", 404))
    e_string = str(site.get("e_string") or "")
    m_string = str(site.get("m_string") or "")

    found = status == e_code and (not e_string or e_string in text)
    missing = status == m_code and (not m_string or m_string in text)

    if found and not missing:
        return "found"
    if missing and not found:
        return "not_found"
    if found and missing:
        if e_string and not m_string:
            return "found"
        if m_string and not e_string:
            return "not_found"
        return "unknown"
    return "unknown"


def extract_metadata(html: str, url: str, username: str) -> dict[str, Any]:
    if not html or len(html) < 40:
        return {}
    soup = BeautifulSoup(html[:2_000_000], "html.parser")

    def meta(*keys: tuple[str, str]) -> str | None:
        for attr, key in keys:
            tag = soup.find("meta", attrs={attr: key})
            if tag and tag.get("content"):
                return str(tag["content"]).strip()[:1000]
        return None

    title = meta(("property", "og:title"), ("name", "twitter:title"))
    if not title and soup.title and soup.title.string:
        title = soup.title.string.strip()[:300]
    description = meta(
        ("property", "og:description"),
        ("name", "description"),
        ("name", "twitter:description"),
    )
    avatar = meta(("property", "og:image"), ("name", "twitter:image"))
    canonical = None
    canonical_tag = soup.find("link", rel=lambda value: value and "canonical" in value)
    if canonical_tag and canonical_tag.get("href"):
        canonical = str(canonical_tag["href"])[:1000]

    haystack = " ".join(filter(None, [title, description, canonical, url])).lower()
    return {
        "title": title,
        "description": description,
        "avatar": avatar,
        "canonical": canonical,
        "username_visible": username.lower() in haystack,
    }


async def load_sites(cache_path: Path, refresh: bool = False) -> tuple[list[dict[str, Any]], str]:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists() and not refresh:
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            sites = data.get("sites", data) if isinstance(data, dict) else data
            if isinstance(sites, list) and sites:
                return [s for s in sites if s.get("valid", True)], "cache"
        except Exception:
            pass

    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(WMN_URL, headers={"User-Agent": DEFAULT_UA})
            response.raise_for_status()
            data = response.json()
        cache_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        sites = data.get("sites", data) if isinstance(data, dict) else data
        if isinstance(sites, list) and sites:
            return [s for s in sites if s.get("valid", True)], "network"
    except Exception:
        pass

    return FALLBACK_SITES.copy(), "fallback"


async def _probe(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    site: dict[str, Any],
    username: str,
) -> dict[str, Any]:
    name = str(site.get("name") or "Unknown")
    uri_check = str(site.get("uri_check") or "")
    uri_pretty = str(site.get("uri_pretty") or uri_check)
    if not uri_check:
        return {"site": name, "status": "error", "error": "missing uri_check"}

    check_url = _format_template(uri_check, username)
    pretty_url = _format_template(uri_pretty, username)
    post_body = site.get("post_body")

    try:
        async with semaphore:
            if post_body:
                body = _format_template(str(post_body), username)
                response = await client.post(
                    check_url,
                    content=body,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            else:
                response = await client.get(check_url)
        text = response.text[:2_000_000]
        status = classify_response(site, response.status_code, text)
        result: dict[str, Any] = {
            "site": name,
            "category": site.get("cat") or "other",
            "status": status,
            "http_status": response.status_code,
            "profile_url": pretty_url,
            "check_url": check_url,
        }
        if status == "found":
            result["metadata"] = extract_metadata(text, str(response.url), username)
        return result
    except httpx.TimeoutException:
        return {"site": name, "category": site.get("cat") or "other", "status": "error", "error": "timeout", "profile_url": pretty_url}
    except Exception as exc:
        return {"site": name, "category": site.get("cat") or "other", "status": "error", "error": str(exc)[:250], "profile_url": pretty_url}


async def scan_username(
    username: str,
    sites: list[dict[str, Any]],
    config: ScanConfig,
    progress: Callable[[int, int, dict[str, Any]], Awaitable[None]] | None = None,
) -> list[dict[str, Any]]:
    username = normalize_username(username)
    filtered = [s for s in sites if s.get("valid", True) and s.get("uri_check")]
    if config.max_sites:
        filtered = filtered[: config.max_sites]

    semaphore = asyncio.Semaphore(max(1, min(config.concurrency, 80)))
    limits = httpx.Limits(max_connections=max(config.concurrency, 10), max_keepalive_connections=20)
    headers = {"User-Agent": DEFAULT_UA, "Accept-Language": "en-US,en;q=0.8"}
    timeout = httpx.Timeout(config.timeout)

    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        headers=headers,
        limits=limits,
    ) as client:
        tasks = [asyncio.create_task(_probe(client, semaphore, site, username)) for site in filtered]
        total = len(tasks)
        done = 0
        for task in asyncio.as_completed(tasks):
            result = await task
            results.append(result)
            done += 1
            if progress:
                await progress(done, total, result)

    order = {"found": 0, "unknown": 1, "error": 2, "not_found": 3}
    results.sort(key=lambda item: (order.get(item.get("status", "unknown"), 9), item.get("site", "").lower()))
    return results


def summarize_counts(results: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"found": 0, "not_found": 0, "unknown": 0, "error": 0}
    for result in results:
        key = result.get("status", "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts
