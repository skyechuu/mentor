import time
from collections import deque

import requests
from bs4 import BeautifulSoup

from doctoskill.robots import DEFAULT_USER_AGENT
from doctoskill.urlutil import (
    canonicalize_url,
    is_under_prefix,
    path_prefix,
    resolve_link,
    same_domain,
)


def _default_fetch(url: str) -> str:
    response = requests.get(
        url,
        timeout=10,
        headers={"User-Agent": DEFAULT_USER_AGENT},
    )
    response.raise_for_status()
    return response.text


def crawl_path_prefix(
    start_url: str,
    max_pages: int = 500,
    delay: float = 0.5,
    fetch_fn=None,
    sleep_fn=None,
    allowed_fn=None,
) -> list[str]:
    """Breadth-first crawl constrained to the start URL's origin and directory."""
    if max_pages < 1:
        return []
    fetch_fn = fetch_fn or _default_fetch
    sleep_fn = sleep_fn or time.sleep
    allowed_fn = allowed_fn or (lambda _url: True)
    start_url = canonicalize_url(start_url)
    prefix = path_prefix(start_url)

    seen = {start_url}
    queue = deque([start_url])
    order: list[str] = []

    while queue and len(order) < max_pages:
        url = queue.popleft()
        if not allowed_fn(url):
            continue
        order.append(url)
        try:
            html = fetch_fn(url)
        except Exception:
            continue

        soup = BeautifulSoup(html, "html.parser")
        for anchor in soup.find_all("a", href=True):
            link = resolve_link(url, anchor.get("href"))
            if (
                link
                and same_domain(link, start_url)
                and is_under_prefix(link, prefix)
                and link not in seen
            ):
                seen.add(link)
                queue.append(link)

        if queue and delay > 0:
            sleep_fn(delay)

    return order
