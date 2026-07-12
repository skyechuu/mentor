import re
import time
from collections import Counter, deque
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

import requests
from bs4 import BeautifulSoup

from doctoskill.content import select_content
from doctoskill.robots import DEFAULT_USER_AGENT
from doctoskill.urlutil import (
    canonicalize_url,
    is_under_prefix,
    path_prefix,
    resolve_link,
    same_domain,
)

TOKEN_RE = re.compile(r"[a-z0-9]{3,}")
CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
FAMILY_RE = re.compile(r"^([A-Za-z]{3,})[-_]")
SCOPE_STOPWORDS = {
    "about",
    "advanced",
    "after",
    "before",
    "complete",
    "create",
    "documentation",
    "example",
    "examples",
    "getting",
    "guide",
    "introduction",
    "learn",
    "manual",
    "more",
    "overview",
    "reference",
    "started",
    "support",
    "tool",
    "tools",
    "unity",
    "using",
    "with",
    "work",
}


def _scope_tokens(text: str) -> set[str]:
    text = CAMEL_BOUNDARY_RE.sub(" ", unquote(text))
    return set(TOKEN_RE.findall(text.lower())) - SCOPE_STOPWORDS


class SectionScope:
    def __init__(
        self,
        seeds: set[str],
        keywords: set[str],
        directory_prefixes: set[str],
        filename_families: set[str],
    ):
        self.seeds = seeds
        self.keywords = keywords
        self.directory_prefixes = directory_prefixes
        self.filename_families = filename_families
        self.enabled = len(seeds) >= 5 and (
            len(keywords) >= 5 or directory_prefixes or filename_families
        )

    def allows(self, url: str, label: str) -> bool:
        if not self.enabled or url in self.seeds:
            return True
        path = urlsplit(url).path
        if any(path.startswith(prefix) for prefix in self.directory_prefixes):
            return True
        stem = PurePosixPath(path).stem.lower()
        if any(stem.startswith(family) for family in self.filename_families):
            return True
        candidate_tokens = _scope_tokens(f"{label} {path}")
        return len(candidate_tokens & self.keywords) >= 2


def _build_section_scope(start_url: str, content, links: list[tuple[str, str]]) -> SectionScope:
    seeds = {url for url, _label in links}
    heading_text = " ".join(
        heading.get_text(" ", strip=True) for heading in content.select("h1, h2, h3")
    )
    label_text = " ".join(label for _url, label in links)
    keywords = _scope_tokens(f"{heading_text} {label_text}")

    base_path = urlsplit(path_prefix(start_url)).path
    directory_prefixes: set[str] = set()
    family_counts: Counter[str] = Counter()
    for url in seeds:
        path = urlsplit(url).path
        directory = path.rsplit("/", 1)[0] + "/"
        if directory != base_path and directory.startswith(base_path):
            directory_prefixes.add(directory)
        family_match = FAMILY_RE.match(PurePosixPath(path).stem)
        if family_match:
            family_counts[family_match.group(1).lower()] += 1
    filename_families = {
        family for family, count in family_counts.items() if count >= 2
    }
    return SectionScope(seeds, keywords, directory_prefixes, filename_families)


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
    progress_fn=None,
    content_selector=None,
    semantic_scope: bool = True,
) -> list[str]:
    """Breadth-first crawl constrained to the start URL's origin and directory."""
    if max_pages < 1:
        return []
    fetch_fn = fetch_fn or _default_fetch
    sleep_fn = sleep_fn or time.sleep
    allowed_fn = allowed_fn or (lambda _url: True)
    progress_fn = progress_fn or (lambda _message: None)
    start_url = canonicalize_url(start_url)
    prefix = path_prefix(start_url)

    seen = {start_url}
    queue = deque([start_url])
    order: list[str] = []
    section_scope = SectionScope(set(), set(), set(), set())

    while queue and len(order) < max_pages:
        url = queue.popleft()
        if not allowed_fn(url):
            progress_fn(f"Skipping disallowed URL: {url}")
            continue
        order.append(url)
        progress_fn(f"Crawling page {len(order)}/{max_pages}: {url}")
        try:
            html = fetch_fn(url)
        except Exception as exc:
            progress_fn(f"Crawl fetch failed for {url}: {exc}")
            continue

        soup = BeautifulSoup(html, "html.parser")
        content = select_content(soup, content_selector)
        if content is None:
            content = soup.body or soup
        for boilerplate in content.select("nav, header, footer, aside, script, style"):
            boilerplate.decompose()
        resolved_links: list[tuple[str, str]] = []
        for anchor in content.find_all("a", href=True):
            link = resolve_link(url, anchor.get("href"))
            if link and same_domain(link, start_url) and is_under_prefix(link, prefix):
                resolved_links.append((link, anchor.get_text(" ", strip=True)))

        if semantic_scope and url == start_url:
            section_scope = _build_section_scope(start_url, content, resolved_links)
            if section_scope.enabled:
                progress_fn(
                    "Section-aware crawl enabled: "
                    f"{len(section_scope.seeds)} seeds, "
                    f"{len(section_scope.directory_prefixes)} directories, "
                    f"{len(section_scope.filename_families)} URL families."
                )

        for link, label in resolved_links:
            if (
                link not in seen
                and (url == start_url or section_scope.allows(link, label))
            ):
                seen.add(link)
                queue.append(link)

        if queue and delay > 0:
            sleep_fn(delay)

    return order
