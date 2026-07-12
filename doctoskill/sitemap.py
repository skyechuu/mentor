import time
import xml.etree.ElementTree as ET
from pathlib import PurePosixPath
from typing import Optional
from urllib.parse import urlsplit

import requests

from doctoskill.urlutil import is_under_prefix

DEFAULT_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_MAX_CHILD_SITEMAPS = 3
DEFAULT_TIME_BUDGET = 15.0


class SitemapTooLargeError(Exception):
    pass


def _request(session, url: str, timeout: float):
    try:
        return session.get(url, timeout=timeout, stream=True)
    except TypeError:
        # Small fake/custom sessions may not implement requests' stream option.
        return session.get(url, timeout=timeout)


def _read_response_text(response, max_bytes: int) -> str:
    headers = getattr(response, "headers", {})
    content_length = headers.get("Content-Length") if headers else None
    if content_length and int(content_length) > max_bytes:
        raise SitemapTooLargeError(f"declared size exceeds {max_bytes} bytes")

    if hasattr(response, "iter_content"):
        chunks: list[bytes] = []
        size = 0
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            size += len(chunk)
            if size > max_bytes:
                raise SitemapTooLargeError(f"stream exceeds {max_bytes} bytes")
            chunks.append(chunk)
        encoding = getattr(response, "encoding", None) or "utf-8"
        return b"".join(chunks).decode(encoding, errors="replace")

    text = response.text
    if len(text.encode("utf-8")) > max_bytes:
        raise SitemapTooLargeError(f"document exceeds {max_bytes} bytes")
    return text


def _fetch_xml(url: str, session, timeout: float, max_bytes: int) -> Optional[ET.Element]:
    response = None
    try:
        response = _request(session, url, timeout)
        if response.status_code >= 400:
            return None
        text = _read_response_text(response, max_bytes)
    except SitemapTooLargeError:
        raise
    except Exception:
        return None
    finally:
        if response is not None and hasattr(response, "close"):
            response.close()

    if not text.strip():
        return None
    try:
        return ET.fromstring(text)
    except ET.ParseError:
        return None


def _locations(root: ET.Element) -> list[str]:
    return [
        element.text.strip()
        for element in root.iter()
        if element.tag.endswith("loc") and element.text and element.text.strip()
    ]


def _prioritize_sitemaps(urls: list[str], prefix: Optional[str]) -> list[str]:
    if not prefix:
        return urls
    path_tokens = {
        token.lower()
        for token in PurePosixPath(urlsplit(prefix).path).parts
        if token not in {"/", ""}
    }
    return sorted(
        urls,
        key=lambda url: (
            not any(token in url.lower() for token in path_tokens),
            urls.index(url),
        ),
    )


def fetch_sitemap_urls(
    domain_root: str,
    session=None,
    timeout: float = 10.0,
    prefix: Optional[str] = None,
    max_urls: Optional[int] = None,
    progress_fn=None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_child_sitemaps: int = DEFAULT_MAX_CHILD_SITEMAPS,
    time_budget: float = DEFAULT_TIME_BUDGET,
) -> Optional[list[str]]:
    """Fetch a bounded sitemap, expanding only a few manageable child maps."""
    session = session or requests
    progress_fn = progress_fn or (lambda _message: None)
    root_url = f"{domain_root.rstrip('/')}/sitemap.xml"
    try:
        root = _fetch_xml(root_url, session, timeout, max_bytes)
    except SitemapTooLargeError as exc:
        progress_fn(f"Skipping oversized sitemap.xml: {exc}")
        return None
    if root is None:
        return None

    locations = _locations(root)
    if not root.tag.endswith("sitemapindex"):
        urls = filter_by_prefix(locations, prefix) if prefix else locations
        return list(dict.fromkeys(urls[:max_urls] if max_urls else urls)) or None

    candidates = _prioritize_sitemaps(locations, prefix)
    inspection_limit = min(len(candidates), max_child_sitemaps)
    progress_fn(
        f"Sitemap index lists {len(candidates)} child maps; "
        f"inspecting at most {inspection_limit}."
    )
    deadline = time.monotonic() + time_budget
    urls: list[str] = []
    seen: set[str] = set()
    for index, sitemap_url in enumerate(candidates[:inspection_limit], start=1):
        if time.monotonic() >= deadline:
            progress_fn("Sitemap inspection time budget reached; falling back.")
            break
        progress_fn(f"Inspecting child sitemap {index}/{inspection_limit}: {sitemap_url}")
        try:
            child = _fetch_xml(sitemap_url, session, timeout, max_bytes)
        except SitemapTooLargeError as exc:
            progress_fn(f"Skipping oversized child sitemap: {exc}")
            continue
        if child is None:
            continue
        child_locations = _locations(child)
        if prefix:
            child_locations = filter_by_prefix(child_locations, prefix)
        for url in child_locations:
            if url not in seen:
                seen.add(url)
                urls.append(url)
                if max_urls and len(urls) >= max_urls:
                    return urls
    return urls or None


def filter_by_prefix(urls: list[str], prefix: str) -> list[str]:
    return [url for url in urls if is_under_prefix(url, prefix)]
