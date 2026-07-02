# DocToSkill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI tool that crawls a live documentation website and converts it into a vendor-neutral Agent Skill (`SKILL.md` + `references/*.md`), per `docs/superpowers/specs/2026-07-02-doctoskill-design.md`.

**Architecture:** A small package (`doctoskill/`) of focused, independently-testable modules — URL/text utilities, four discovery strategies tried in priority order (llms.txt, nav-tree, sitemap, path-prefix crawl), a fetch layer with HTTP-then-headless fallback and on-disk caching, an HTML→Markdown converter, a hierarchy resolver, and an assembler that writes the final skill folder. `cli.py` wires these together; every other module has zero dependency on `cli.py` and can be tested in isolation.

**Tech Stack:** Python 3.10+, `requests`, `beautifulsoup4`, `markdownify`; `playwright` and `anthropic` as lazy-imported optional extras. `pytest` for tests.

## Global Constraints

- Python 3.10+ (required for `X | None` union-type annotations used throughout, e.g. in dataclass fields). Package lives at `doctoskill/`, tests at `tests/`, fixtures at `tests/fixtures/`.
- CLI invocation: `python3 -m doctoskill <start-url> --output <dir> --name <name> --max-pages N --delay S --config <file> --skip-scrape --zip --enhance`. (This replaces the spec's illustrative `doctoskill.py <start-url> ...` — a top-level `doctoskill.py` script would collide with the `doctoskill/` package directory of the same name on import. `python3 -m doctoskill` is the standard equivalent; all flags are unchanged.)
- Required dependencies: `requests`, `beautifulsoup4`, `markdownify`. `playwright` (headless fallback) and `anthropic` (`--enhance`) are lazy-imported inside the functions that need them — never imported at module load time, never required for a default run.
- Discovery order, first success wins, `--config` fields override the corresponding step: **llms.txt** (`llms-full.txt` then `llms.txt` at domain root) → **nav-tree** (DocFX `toc.html` format first, generic sidebar heuristic second) → **sitemap.xml** (filtered to the start URL's path prefix) → **path-prefix BFS link crawl** (same domain, same path prefix, default `--max-pages` 500, default `--delay` 0.5s).
- Output: `<output>/<name>/SKILL.md` + `<output>/<name>/references/**/*.md`. YAML frontmatter uses only plain `name`/`description` fields — no vendor-specific keys. Output is deterministic (no LLM call) unless `--enhance` is passed.
- Politeness: check `robots.txt` before crawling; if the entire start-url path is disallowed, print a clear message to stderr and exit with code 2 without crawling anything.
- Cache: raw fetched HTML is cached at `<output>/<name>/.cache/<sha256(url)>.html`; `.cache/` is excluded from `--zip` output.
- Scope: one skill per crawl root. The tool never auto-discovers or merges sibling doc sections (e.g. a separate API-reference nav tree) — that requires a second run with a different start URL.

---

### Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `doctoskill/__init__.py`
- Create: `doctoskill/__main__.py`
- Create: `doctoskill/cli.py`
- Create: `doctoskill/types.py`
- Test: `tests/test_cli_scaffolding.py`

**Interfaces:**
- Produces: `doctoskill.cli.build_arg_parser() -> argparse.ArgumentParser`, `doctoskill.cli.main(argv: list[str] | None = None) -> int`, `doctoskill.types.ConvertedPage` dataclass with fields `title: str`, `markdown: str`, `path_segments: list[str]`, `url: str | None = None`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli_scaffolding.py
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_module_help_runs():
    result = subprocess.run(
        [sys.executable, "-m", "doctoskill", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "start_url" in result.stdout


def test_converted_page_defaults():
    from doctoskill.types import ConvertedPage

    page = ConvertedPage(title="Intro", markdown="# Intro", path_segments=["guide"])
    assert page.url is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli_scaffolding.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'doctoskill'`

- [ ] **Step 3: Write minimal implementation**

```toml
# pyproject.toml
[project]
name = "doctoskill"
version = "0.1.0"
description = "Convert a documentation website into an Agent Skill"
requires-python = ">=3.10"
dependencies = [
    "requests>=2.31",
    "beautifulsoup4>=4.12",
    "markdownify>=0.11",
]

[project.optional-dependencies]
playwright = ["playwright>=1.40"]
enhance = ["anthropic>=0.25"]
dev = ["pytest>=7.4"]

[project.scripts]
doctoskill = "doctoskill.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["doctoskill*"]
```

```python
# doctoskill/__init__.py
```

```python
# doctoskill/types.py
from dataclasses import dataclass


@dataclass
class ConvertedPage:
    title: str
    markdown: str
    path_segments: list[str]
    url: str | None = None
```

```python
# doctoskill/cli.py
import argparse


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="doctoskill",
        description="Convert a documentation website into an Agent Skill.",
    )
    parser.add_argument("start_url", help="First page of the docs to crawl")
    parser.add_argument("--output", default="./skills")
    parser.add_argument("--name", default=None)
    parser.add_argument("--max-pages", type=int, default=500)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--config", default=None)
    parser.add_argument("--skip-scrape", action="store_true")
    parser.add_argument("--zip", action="store_true")
    parser.add_argument("--enhance", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    parser.parse_args(argv)
    return 0
```

```python
# doctoskill/__main__.py
import sys

from doctoskill.cli import main

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli_scaffolding.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml doctoskill/__init__.py doctoskill/__main__.py doctoskill/cli.py doctoskill/types.py tests/test_cli_scaffolding.py
git commit -m "Scaffold doctoskill package and CLI skeleton"
```

---

### Task 2: slugify and URL utilities

**Files:**
- Create: `doctoskill/slugify.py`
- Create: `doctoskill/urlutil.py`
- Test: `tests/test_slugify.py`
- Test: `tests/test_urlutil.py`

**Interfaces:**
- Produces: `doctoskill.slugify.slugify(text: str) -> str`; `doctoskill.urlutil.same_domain(url_a: str, url_b: str) -> bool`, `doctoskill.urlutil.path_prefix(url: str) -> str`, `doctoskill.urlutil.is_under_prefix(url: str, prefix: str) -> bool`, `doctoskill.urlutil.resolve_link(base_url: str, href: str | None) -> str | None`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_slugify.py
from doctoskill.slugify import slugify


def test_basic_title():
    assert slugify("Getting Started") == "getting-started"


def test_apostrophe_and_punctuation():
    assert slugify("What's new!!") == "what-s-new"


def test_empty_string_falls_back():
    assert slugify("   ") == "untitled"
```

```python
# tests/test_urlutil.py
from doctoskill.urlutil import is_under_prefix, path_prefix, resolve_link, same_domain


def test_same_domain_true():
    assert same_domain("https://example.com/a", "https://example.com/b") is True


def test_same_domain_false():
    assert same_domain("https://example.com/a", "https://other.com/b") is False


def test_path_prefix_from_index_page():
    assert path_prefix("https://docs.example.com/manual/index.html") == "https://docs.example.com/manual/"


def test_is_under_prefix():
    prefix = "https://docs.example.com/manual/"
    assert is_under_prefix("https://docs.example.com/manual/whats-new.html", prefix) is True
    assert is_under_prefix("https://docs.example.com/blog/post.html", prefix) is False


def test_resolve_link_relative():
    result = resolve_link("https://docs.example.com/manual/index.html", "whats-new.html")
    assert result == "https://docs.example.com/manual/whats-new.html"


def test_resolve_link_strips_fragment():
    result = resolve_link("https://docs.example.com/manual/index.html", "index.html#section")
    assert result == "https://docs.example.com/manual/index.html"


def test_resolve_link_rejects_mailto():
    assert resolve_link("https://docs.example.com/manual/index.html", "mailto:a@b.com") is None


def test_resolve_link_rejects_empty():
    assert resolve_link("https://docs.example.com/manual/index.html", None) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_slugify.py tests/test_urlutil.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'doctoskill.slugify'`

- [ ] **Step 3: Write minimal implementation**

```python
# doctoskill/slugify.py
import re


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "untitled"
```

```python
# doctoskill/urlutil.py
from urllib.parse import urljoin, urlsplit, urlunsplit


def same_domain(url_a: str, url_b: str) -> bool:
    return urlsplit(url_a).netloc == urlsplit(url_b).netloc


def path_prefix(url: str) -> str:
    parts = urlsplit(url)
    path = parts.path
    if not path.endswith("/"):
        path = path.rsplit("/", 1)[0] + "/"
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def is_under_prefix(url: str, prefix: str) -> bool:
    return url.startswith(prefix)


def resolve_link(base_url: str, href: str | None) -> str | None:
    if not href:
        return None
    href = href.split("#")[0]
    if not href or href.startswith(("mailto:", "javascript:", "tel:")):
        return None
    resolved = urljoin(base_url, href)
    if urlsplit(resolved).scheme not in ("http", "https"):
        return None
    return resolved
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_slugify.py tests/test_urlutil.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Commit**

```bash
git add doctoskill/slugify.py doctoskill/urlutil.py tests/test_slugify.py tests/test_urlutil.py
git commit -m "Add slugify and URL utility functions"
```

---

### Task 3: robots.txt politeness check

**Files:**
- Create: `doctoskill/robots.py`
- Test: `tests/test_robots.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `doctoskill.robots.can_crawl(start_url: str, session=None, timeout: float = 10.0) -> bool`, `doctoskill.robots.DEFAULT_USER_AGENT: str`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_robots.py
from doctoskill.robots import can_crawl


class FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code


class FakeSession:
    def __init__(self, robots_text=None, raise_exc=None):
        self.robots_text = robots_text
        self.raise_exc = raise_exc

    def get(self, url, timeout=10, headers=None):
        if self.raise_exc:
            raise self.raise_exc
        return FakeResponse(self.robots_text)


def test_disallowed_path_returns_false():
    session = FakeSession(robots_text="User-agent: *\nDisallow: /manual/\n")
    assert can_crawl("https://docs.example.com/manual/index.html", session=session) is False


def test_allowed_path_returns_true():
    session = FakeSession(robots_text="User-agent: *\nDisallow: /manual/\n")
    assert can_crawl("https://docs.example.com/other/index.html", session=session) is True


def test_missing_robots_defaults_to_allowed():
    session = FakeSession(raise_exc=ConnectionError("no route"))
    assert can_crawl("https://docs.example.com/manual/index.html", session=session) is True


def test_no_disallow_rules_defaults_to_allowed():
    session = FakeSession(robots_text="User-agent: *\n")
    assert can_crawl("https://docs.example.com/manual/index.html", session=session) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_robots.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'doctoskill.robots'`

- [ ] **Step 3: Write minimal implementation**

```python
# doctoskill/robots.py
import urllib.robotparser as robotparser
from urllib.parse import urlsplit, urlunsplit

import requests

DEFAULT_USER_AGENT = "DocToSkillBot/0.1"


def can_crawl(start_url: str, session=None, timeout: float = 10.0) -> bool:
    parts = urlsplit(start_url)
    robots_url = urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))
    session = session or requests
    try:
        resp = session.get(robots_url, timeout=timeout, headers={"User-Agent": DEFAULT_USER_AGENT})
        if resp.status_code >= 400:
            return True
        text = resp.text
    except Exception:
        return True
    parser = robotparser.RobotFileParser()
    parser.parse(text.splitlines())
    return parser.can_fetch(DEFAULT_USER_AGENT, start_url)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_robots.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add doctoskill/robots.py tests/test_robots.py
git commit -m "Add robots.txt politeness check"
```

---

### Task 4: llms.txt discovery and parsing

**Files:**
- Create: `doctoskill/llms_txt.py`
- Create: `tests/fixtures/llms_full.txt`
- Test: `tests/test_llms_txt.py`

**Interfaces:**
- Produces: `doctoskill.llms_txt.fetch_llms_txt(domain_root: str, session=None, timeout: float = 10.0) -> str | None`, `doctoskill.llms_txt.parse_llms_txt(text: str) -> list[tuple[str, str]]`.

- [ ] **Step 1: Write the failing test**

```
# tests/fixtures/llms_full.txt
# Example Framework

## Getting Started

Example framework getting started content goes here with a code sample.

```py
print("hello")
```

## Configuration

Configuration content here.
```

```python
# tests/test_llms_txt.py
from pathlib import Path

from doctoskill.llms_txt import fetch_llms_txt, parse_llms_txt

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_llms_txt_splits_into_sections():
    text = (FIXTURES / "llms_full.txt").read_text(encoding="utf-8")
    sections = parse_llms_txt(text)
    assert [title for title, _ in sections] == ["Getting Started", "Configuration"]
    assert "print(\"hello\")" in sections[0][1]
    assert sections[1][1] == "Configuration content here."


class FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code


class FakeSession:
    def __init__(self, ok_urls):
        self.ok_urls = ok_urls

    def get(self, url, timeout=10, headers=None):
        if url in self.ok_urls:
            return FakeResponse(self.ok_urls[url])
        return FakeResponse("", status_code=404)


def test_fetch_llms_txt_prefers_full():
    session = FakeSession(
        {
            "https://example.com/llms-full.txt": "full content",
            "https://example.com/llms.txt": "short content",
        }
    )
    assert fetch_llms_txt("https://example.com", session=session) == "full content"


def test_fetch_llms_txt_falls_back_to_short():
    session = FakeSession({"https://example.com/llms.txt": "short content"})
    assert fetch_llms_txt("https://example.com", session=session) == "short content"


def test_fetch_llms_txt_returns_none_when_absent():
    session = FakeSession({})
    assert fetch_llms_txt("https://example.com", session=session) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_llms_txt.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'doctoskill.llms_txt'`

- [ ] **Step 3: Write minimal implementation**

```python
# doctoskill/llms_txt.py
import requests

CANDIDATE_FILES = ("llms-full.txt", "llms.txt")


def fetch_llms_txt(domain_root: str, session=None, timeout: float = 10.0) -> str | None:
    session = session or requests
    base = domain_root.rstrip("/")
    for filename in CANDIDATE_FILES:
        url = f"{base}/{filename}"
        try:
            resp = session.get(url, timeout=timeout)
        except Exception:
            continue
        if resp.status_code < 400 and resp.text.strip():
            return resp.text
    return None


def parse_llms_txt(text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    sections: list[tuple[str, str]] = []
    current_title: str | None = None
    current_lines: list[str] = []
    preamble_lines: list[str] = []

    for line in lines:
        if line.startswith("## "):
            if current_title is not None:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = line[3:].strip()
            current_lines = []
        elif current_title is not None:
            current_lines.append(line)
        else:
            preamble_lines.append(line)

    if current_title is not None:
        sections.append((current_title, "\n".join(current_lines).strip()))
    return sections
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_llms_txt.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add doctoskill/llms_txt.py tests/fixtures/llms_full.txt tests/test_llms_txt.py
git commit -m "Add llms.txt discovery and section parsing"
```

---

### Task 5: sitemap.xml discovery

**Files:**
- Create: `doctoskill/sitemap.py`
- Create: `tests/fixtures/sitemap.xml`
- Test: `tests/test_sitemap.py`

**Interfaces:**
- Produces: `doctoskill.sitemap.fetch_sitemap_urls(domain_root: str, session=None, timeout: float = 10.0) -> list[str] | None`, `doctoskill.sitemap.filter_by_prefix(urls: list[str], prefix: str) -> list[str]`.

- [ ] **Step 1: Write the failing test**

```xml
<!-- tests/fixtures/sitemap.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/docs/guide/intro</loc></url>
  <url><loc>https://example.com/docs/guide/setup</loc></url>
  <url><loc>https://example.com/blog/post-1</loc></url>
</urlset>
```

```python
# tests/test_sitemap.py
from pathlib import Path

from doctoskill.sitemap import fetch_sitemap_urls, filter_by_prefix

FIXTURES = Path(__file__).parent / "fixtures"


class FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code


class FakeSession:
    def __init__(self, ok_urls):
        self.ok_urls = ok_urls

    def get(self, url, timeout=10):
        if url in self.ok_urls:
            return FakeResponse(self.ok_urls[url])
        return FakeResponse("", status_code=404)


def test_fetch_sitemap_urls_parses_locs():
    xml = (FIXTURES / "sitemap.xml").read_text(encoding="utf-8")
    session = FakeSession({"https://example.com/sitemap.xml": xml})
    urls = fetch_sitemap_urls("https://example.com", session=session)
    assert urls == [
        "https://example.com/docs/guide/intro",
        "https://example.com/docs/guide/setup",
        "https://example.com/blog/post-1",
    ]


def test_fetch_sitemap_urls_returns_none_when_missing():
    session = FakeSession({})
    assert fetch_sitemap_urls("https://example.com", session=session) is None


def test_filter_by_prefix():
    urls = [
        "https://example.com/docs/guide/intro",
        "https://example.com/docs/guide/setup",
        "https://example.com/blog/post-1",
    ]
    assert filter_by_prefix(urls, "https://example.com/docs/") == urls[:2]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_sitemap.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'doctoskill.sitemap'`

- [ ] **Step 3: Write minimal implementation**

```python
# doctoskill/sitemap.py
import xml.etree.ElementTree as ET

import requests


def fetch_sitemap_urls(domain_root: str, session=None, timeout: float = 10.0) -> list[str] | None:
    session = session or requests
    url = f"{domain_root.rstrip('/')}/sitemap.xml"
    try:
        resp = session.get(url, timeout=timeout)
    except Exception:
        return None
    if resp.status_code >= 400 or not resp.text.strip():
        return None
    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError:
        return None
    locs = [elem.text.strip() for elem in root.iter() if elem.tag.endswith("loc") and elem.text]
    return locs or None


def filter_by_prefix(urls: list[str], prefix: str) -> list[str]:
    return [u for u in urls if u.startswith(prefix)]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_sitemap.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add doctoskill/sitemap.py tests/fixtures/sitemap.xml tests/test_sitemap.py
git commit -m "Add sitemap.xml discovery"
```

---

### Task 6: NavNode data structure and DocFX TOC parser

**Files:**
- Create: `doctoskill/navtree.py`
- Create: `doctoskill/navtree_docfx.py`
- Create: `tests/fixtures/docfx_toc.html`
- Test: `tests/test_navtree_docfx.py`

**Interfaces:**
- Produces: `doctoskill.navtree.NavNode` dataclass (`title: str`, `url: str | None`, `children: list[NavNode]`), `doctoskill.navtree_docfx.parse_docfx_toc(html: str, base_url: str) -> NavNode | None`.

- [ ] **Step 1: Write the failing test**

```html
<!-- tests/fixtures/docfx_toc.html -->
<div id="sidetoggle">
  <div>
    <div class="sidetoc">
      <div class="toc" id="toc">
        <ul class="nav level1">
          <li>
            <span class="expand-stub"></span>
            <a href="index.html" title="Entities package">Entities package</a>
            <ul class="nav level2">
              <li><a href="whats-new.html" title="What's new">What's new</a></li>
            </ul>
          </li>
          <li>
            <a href="upgrade-guide.html" title="Upgrade guide">Upgrade guide</a>
          </li>
          <li>
            <span class="expand-stub"></span>
            <a href="getting-started.html" title="Get started">Get started</a>
            <ul class="nav level2">
              <li><a href="getting-started-installation.html" title="Installation">Installation</a></li>
              <li>
                <span class="expand-stub"></span>
                <a href="ecs-workflow-tutorial.html" title="ECS workflow examples">ECS workflow examples</a>
                <ul class="nav level3">
                  <li><a href="ecs-workflow-intro.html" title="Introduction to the ECS workflow">Introduction to the ECS workflow</a></li>
                  <li><a href="ecs-workflow-example-starter.html" title="Starter ECS workflow">Starter ECS workflow</a></li>
                </ul>
              </li>
            </ul>
          </li>
        </ul>
      </div>
    </div>
  </div>
</div>
```

```python
# tests/test_navtree_docfx.py
from pathlib import Path

from doctoskill.navtree_docfx import parse_docfx_toc

FIXTURES = Path(__file__).parent / "fixtures"
BASE_URL = "https://docs.unity3d.com/Packages/com.unity.entities@6.4/manual/index.html"


def test_parse_docfx_toc_builds_tree():
    html = (FIXTURES / "docfx_toc.html").read_text(encoding="utf-8")
    root = parse_docfx_toc(html, BASE_URL)
    assert root is not None
    titles = [child.title for child in root.children]
    assert titles == ["Entities package", "Upgrade guide", "Get started"]

    entities_package = root.children[0]
    assert entities_package.url.endswith("index.html")
    assert entities_package.children[0].title == "What's new"
    assert entities_package.children[0].url.endswith("whats-new.html")

    get_started = root.children[2]
    ecs_workflow = get_started.children[1]
    assert ecs_workflow.title == "ECS workflow examples"
    assert ecs_workflow.children[0].title == "Introduction to the ECS workflow"


def test_parse_docfx_toc_returns_none_without_toc():
    assert parse_docfx_toc("<html><body>no toc here</body></html>", BASE_URL) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_navtree_docfx.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'doctoskill.navtree_docfx'`

- [ ] **Step 3: Write minimal implementation**

```python
# doctoskill/navtree.py
from dataclasses import dataclass, field


@dataclass
class NavNode:
    title: str
    url: str | None
    children: list["NavNode"] = field(default_factory=list)
```

```python
# doctoskill/navtree_docfx.py
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from doctoskill.navtree import NavNode


def _walk(ul) -> list[NavNode]:
    nodes = []
    for li in ul.find_all("li", recursive=False):
        a = li.find("a", recursive=False)
        if a is None:
            continue
        title = a.get("title") or a.get_text(strip=True)
        href = a.get("href")
        child_ul = li.find("ul", recursive=False)
        children = _walk(child_ul) if child_ul is not None else []
        nodes.append(NavNode(title=title, url=href, children=children))
    return nodes


def parse_docfx_toc(html: str, base_url: str) -> NavNode | None:
    soup = BeautifulSoup(html, "html.parser")
    top_ul = soup.select_one("div#toc ul.nav")
    if top_ul is None:
        return None
    children = _walk(top_ul)
    if not children:
        return None
    for node in _flatten(children):
        if node.url:
            node.url = urljoin(base_url, node.url)
    return NavNode(title="root", url=None, children=children)


def _flatten(nodes: list[NavNode]):
    for node in nodes:
        yield node
        yield from _flatten(node.children)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_navtree_docfx.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add doctoskill/navtree.py doctoskill/navtree_docfx.py tests/fixtures/docfx_toc.html tests/test_navtree_docfx.py
git commit -m "Add NavNode structure and DocFX toc.html parser"
```

---

### Task 7: Generic nav-tree heuristic parser

**Files:**
- Create: `doctoskill/navtree_generic.py`
- Create: `tests/fixtures/generic_sidebar.html`
- Test: `tests/test_navtree_generic.py`

**Interfaces:**
- Consumes: `doctoskill.navtree.NavNode` (Task 6).
- Produces: `doctoskill.navtree_generic.parse_generic_navtree(html: str, base_url: str, nav_selector: str | None = None) -> NavNode | None`.

- [ ] **Step 1: Write the failing test**

```html
<!-- tests/fixtures/generic_sidebar.html -->
<html>
<body>
<nav class="md-nav">
  <ul>
    <li><a href="/guide/intro/">Introduction</a></li>
    <li>
      <a href="/guide/setup/">Setup</a>
      <ul>
        <li><a href="/guide/setup/install/">Install</a></li>
        <li><a href="/guide/setup/config/">Configure</a></li>
      </ul>
    </li>
  </ul>
</nav>
</body>
</html>
```

```python
# tests/test_navtree_generic.py
from pathlib import Path

from doctoskill.navtree_generic import parse_generic_navtree

FIXTURES = Path(__file__).parent / "fixtures"
BASE_URL = "https://example.com/guide/index.html"


def test_parse_generic_navtree_builds_tree():
    html = (FIXTURES / "generic_sidebar.html").read_text(encoding="utf-8")
    root = parse_generic_navtree(html, BASE_URL)
    assert root is not None
    titles = [child.title for child in root.children]
    assert titles == ["Introduction", "Setup"]
    setup = root.children[1]
    assert [c.title for c in setup.children] == ["Install", "Configure"]


def test_parse_generic_navtree_respects_explicit_selector():
    html = "<html><body><div id='other'><ul><li><a href='/a/'>A</a></li><li><a href='/b/'>B</a></li><li><a href='/c/'>C</a></li></ul></div></body></html>"
    root = parse_generic_navtree(html, BASE_URL, nav_selector="#other")
    assert root is not None
    assert [c.title for c in root.children] == ["A", "B", "C"]


def test_parse_generic_navtree_returns_none_when_no_nav_found():
    assert parse_generic_navtree("<html><body><p>no nav</p></body></html>", BASE_URL) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_navtree_generic.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'doctoskill.navtree_generic'`

- [ ] **Step 3: Write minimal implementation**

```python
# doctoskill/navtree_generic.py
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from doctoskill.navtree import NavNode

MIN_LINKS = 3


def _walk(ul) -> list[NavNode]:
    nodes = []
    for li in ul.find_all("li", recursive=False):
        a = li.find("a", recursive=False)
        if a is None:
            continue
        title = a.get_text(strip=True)
        href = a.get("href")
        child_ul = li.find("ul", recursive=False)
        children = _walk(child_ul) if child_ul is not None else []
        nodes.append(NavNode(title=title, url=href, children=children))
    return nodes


def _flatten(nodes: list[NavNode]):
    for node in nodes:
        yield node
        yield from _flatten(node.children)


def parse_generic_navtree(html: str, base_url: str, nav_selector: str | None = None) -> NavNode | None:
    soup = BeautifulSoup(html, "html.parser")

    if nav_selector:
        candidates = [soup.select_one(nav_selector)]
    else:
        candidates = soup.select("nav, [class*=sidebar], [class*=toc], [class*=nav]")

    best_ul = None
    best_count = 0
    for candidate in candidates:
        if candidate is None:
            continue
        ul = candidate.find("ul")
        if ul is None:
            continue
        link_count = len(ul.find_all("a", href=True))
        if link_count > best_count:
            best_ul = ul
            best_count = link_count

    if best_ul is None or best_count < MIN_LINKS:
        return None

    children = _walk(best_ul)
    if not children:
        return None
    for node in _flatten(children):
        if node.url:
            node.url = urljoin(base_url, node.url)
    return NavNode(title="root", url=None, children=children)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_navtree_generic.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add doctoskill/navtree_generic.py tests/fixtures/generic_sidebar.html tests/test_navtree_generic.py
git commit -m "Add generic nav-tree heuristic parser"
```

---

### Task 8: Path-prefix BFS link crawler

**Files:**
- Create: `doctoskill/crawler.py`
- Test: `tests/test_crawler.py`

**Interfaces:**
- Consumes: `doctoskill.urlutil.{path_prefix, is_under_prefix, resolve_link, same_domain}` (Task 2).
- Produces: `doctoskill.crawler.crawl_path_prefix(start_url: str, max_pages: int = 500, delay: float = 0.5, fetch_fn=None, sleep_fn=None) -> list[str]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_crawler.py
from doctoskill.crawler import crawl_path_prefix

PAGES = {
    "https://example.com/docs/index.html": (
        '<a href="page-a.html">A</a> <a href="page-b.html">B</a> '
        '<a href="https://example.com/blog/post.html">Blog</a>'
    ),
    "https://example.com/docs/page-a.html": '<a href="page-c.html">C</a>',
    "https://example.com/docs/page-b.html": '<a href="index.html">Home</a>',
    "https://example.com/docs/page-c.html": "",
}


def test_crawl_stays_within_prefix_and_domain():
    sleeps = []
    order = crawl_path_prefix(
        "https://example.com/docs/index.html",
        fetch_fn=lambda url: PAGES[url],
        sleep_fn=sleeps.append,
    )
    assert order == [
        "https://example.com/docs/index.html",
        "https://example.com/docs/page-a.html",
        "https://example.com/docs/page-b.html",
        "https://example.com/docs/page-c.html",
    ]
    assert "https://example.com/blog/post.html" not in order


def test_crawl_respects_max_pages():
    order = crawl_path_prefix(
        "https://example.com/docs/index.html",
        max_pages=2,
        fetch_fn=lambda url: PAGES[url],
        sleep_fn=lambda seconds: None,
    )
    assert len(order) == 2


def test_crawl_skips_pages_that_fail_to_fetch():
    def flaky_fetch(url):
        if url.endswith("page-a.html"):
            raise ConnectionError("boom")
        return PAGES[url]

    order = crawl_path_prefix(
        "https://example.com/docs/index.html",
        fetch_fn=flaky_fetch,
        sleep_fn=lambda seconds: None,
    )
    assert "https://example.com/docs/page-a.html" in order
    assert "https://example.com/docs/page-c.html" not in order
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_crawler.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'doctoskill.crawler'`

- [ ] **Step 3: Write minimal implementation**

```python
# doctoskill/crawler.py
import time
from collections import deque

from bs4 import BeautifulSoup

from doctoskill.robots import DEFAULT_USER_AGENT
from doctoskill.urlutil import is_under_prefix, path_prefix, resolve_link, same_domain


def _default_fetch(url: str) -> str:
    import requests

    resp = requests.get(url, timeout=10, headers={"User-Agent": DEFAULT_USER_AGENT})
    resp.raise_for_status()
    return resp.text


def crawl_path_prefix(
    start_url: str,
    max_pages: int = 500,
    delay: float = 0.5,
    fetch_fn=None,
    sleep_fn=None,
) -> list[str]:
    fetch_fn = fetch_fn or _default_fetch
    sleep_fn = sleep_fn or time.sleep
    prefix = path_prefix(start_url)

    seen = {start_url}
    queue = deque([start_url])
    order: list[str] = []

    while queue and len(order) < max_pages:
        url = queue.popleft()
        order.append(url)
        try:
            html = fetch_fn(url)
        except Exception:
            continue

        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            link = resolve_link(url, a["href"])
            if not link:
                continue
            if not same_domain(link, start_url):
                continue
            if not is_under_prefix(link, prefix):
                continue
            if link in seen:
                continue
            seen.add(link)
            queue.append(link)

        if queue:
            sleep_fn(delay)

    return order
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_crawler.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add doctoskill/crawler.py tests/test_crawler.py
git commit -m "Add path-prefix BFS link crawler"
```

---

### Task 9: On-disk page cache

**Files:**
- Create: `doctoskill/cache.py`
- Test: `tests/test_cache.py`

**Interfaces:**
- Produces: `doctoskill.cache.PageCache` with `__init__(self, cache_dir)`, `get(self, url: str) -> str | None`, `put(self, url: str, html: str) -> None`, `has_any(self) -> bool`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cache.py
from doctoskill.cache import PageCache


def test_put_then_get_roundtrips(tmp_path):
    cache = PageCache(tmp_path / "cache")
    cache.put("https://example.com/a", "<html>A</html>")
    assert cache.get("https://example.com/a") == "<html>A</html>"


def test_get_missing_returns_none(tmp_path):
    cache = PageCache(tmp_path / "cache")
    assert cache.get("https://example.com/missing") is None


def test_has_any_false_when_empty(tmp_path):
    cache = PageCache(tmp_path / "cache")
    assert cache.has_any() is False


def test_has_any_true_after_put(tmp_path):
    cache = PageCache(tmp_path / "cache")
    cache.put("https://example.com/a", "<html>A</html>")
    assert cache.has_any() is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cache.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'doctoskill.cache'`

- [ ] **Step 3: Write minimal implementation**

```python
# doctoskill/cache.py
import hashlib
from pathlib import Path


class PageCache:
    def __init__(self, cache_dir):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.html"

    def get(self, url: str) -> str | None:
        path = self._path_for(url)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def put(self, url: str, html: str) -> None:
        self._path_for(url).write_text(html, encoding="utf-8")

    def has_any(self) -> bool:
        return any(self.cache_dir.glob("*.html"))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cache.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add doctoskill/cache.py tests/test_cache.py
git commit -m "Add on-disk page cache"
```

---

### Task 10: Fetch layer with JS-shell detection and headless fallback

**Files:**
- Create: `doctoskill/fetch.py`
- Create: `tests/fixtures/sample_page.html`
- Create: `tests/fixtures/js_shell.html`
- Test: `tests/test_fetch.py`

**Interfaces:**
- Consumes: `doctoskill.cache.PageCache` (Task 9).
- Produces: `doctoskill.fetch.looks_like_js_shell(html: str, content_selector: str | None = None, min_length: int = 200) -> bool`, `doctoskill.fetch.fetch_page(url: str, cache=None, use_cache_only: bool = False, content_selector: str | None = None, session=None, timeout: float = 10.0) -> str`, `doctoskill.fetch.CacheMissError` exception.

- [ ] **Step 1: Write the failing test**

```html
<!-- tests/fixtures/sample_page.html -->
<html>
<head><title>Sample Page Title</title></head>
<body>
<nav class="sidebar">Nav junk should be removed</nav>
<header>Header junk</header>
<main>
<h1>Sample Page Title</h1>
<p>This is the real content of the page that should survive conversion to markdown. It needs to be long enough to not look like a JS shell placeholder so the fetch heuristic treats it as real content already rendered by the server.</p>
<pre><code class="language-python">print("hi")</code></pre>
</main>
<footer>Footer junk</footer>
</body>
</html>
```

```html
<!-- tests/fixtures/js_shell.html -->
<html><head><title>App</title></head><body><div id="root"></div><script src="/app.js"></script></body></html>
```

```python
# tests/test_fetch.py
from pathlib import Path

import doctoskill.fetch as fetch_module
from doctoskill.cache import PageCache
from doctoskill.fetch import CacheMissError, fetch_page, looks_like_js_shell

FIXTURES = Path(__file__).parent / "fixtures"


def test_looks_like_js_shell_false_for_rendered_page():
    html = (FIXTURES / "sample_page.html").read_text(encoding="utf-8")
    assert looks_like_js_shell(html) is False


def test_looks_like_js_shell_true_for_empty_root_div():
    html = (FIXTURES / "js_shell.html").read_text(encoding="utf-8")
    assert looks_like_js_shell(html) is True


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


class FakeSession:
    def __init__(self, text):
        self.text = text

    def get(self, url, timeout=10, headers=None):
        return FakeResponse(self.text)


def test_fetch_page_returns_html_directly_when_not_a_shell():
    html = (FIXTURES / "sample_page.html").read_text(encoding="utf-8")
    session = FakeSession(html)
    result = fetch_page("https://example.com/page", session=session)
    assert result == html


def test_fetch_page_falls_back_to_headless_for_shell(monkeypatch):
    shell_html = (FIXTURES / "js_shell.html").read_text(encoding="utf-8")
    rendered_html = (FIXTURES / "sample_page.html").read_text(encoding="utf-8")
    session = FakeSession(shell_html)

    monkeypatch.setattr(fetch_module, "_render_with_playwright", lambda url, timeout=10.0: rendered_html)

    result = fetch_page("https://example.com/page", session=session)
    assert result == rendered_html


def test_fetch_page_uses_and_populates_cache(tmp_path):
    html = (FIXTURES / "sample_page.html").read_text(encoding="utf-8")
    session = FakeSession(html)
    cache = PageCache(tmp_path / "cache")

    result = fetch_page("https://example.com/page", cache=cache, session=session)
    assert result == html
    assert cache.get("https://example.com/page") == html


def test_fetch_page_reads_from_cache_without_hitting_session(tmp_path):
    cache = PageCache(tmp_path / "cache")
    cache.put("https://example.com/page", "cached content")

    class ExplodingSession:
        def get(self, *args, **kwargs):
            raise AssertionError("should not be called")

    result = fetch_page("https://example.com/page", cache=cache, session=ExplodingSession())
    assert result == "cached content"


def test_fetch_page_raises_cache_miss_when_use_cache_only(tmp_path):
    cache = PageCache(tmp_path / "cache")

    class ExplodingSession:
        def get(self, *args, **kwargs):
            raise AssertionError("should not be called")

    try:
        fetch_page("https://example.com/page", cache=cache, use_cache_only=True, session=ExplodingSession())
        assert False, "expected CacheMissError"
    except CacheMissError:
        pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_fetch.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'doctoskill.fetch'`

- [ ] **Step 3: Write minimal implementation**

```python
# doctoskill/fetch.py
from bs4 import BeautifulSoup

from doctoskill.robots import DEFAULT_USER_AGENT

CONTENT_SELECTOR_FALLBACKS = "main, article, [role=main], #content, .content"


class CacheMissError(Exception):
    pass


def looks_like_js_shell(html: str, content_selector: str | None = None, min_length: int = 200) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    if content_selector:
        element = soup.select_one(content_selector)
    else:
        element = soup.select_one(CONTENT_SELECTOR_FALLBACKS) or soup.body
    text = element.get_text(strip=True) if element else ""
    return len(text) < min_length


def _render_with_playwright(url: str, timeout: float = 10.0) -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(url, timeout=timeout * 1000)
        html = page.content()
        browser.close()
    return html


def fetch_page(
    url: str,
    cache=None,
    use_cache_only: bool = False,
    content_selector: str | None = None,
    session=None,
    timeout: float = 10.0,
) -> str:
    if cache is not None:
        cached = cache.get(url)
        if cached is not None:
            return cached
        if use_cache_only:
            raise CacheMissError(url)

    session = session or __import__("requests")
    resp = session.get(url, timeout=timeout, headers={"User-Agent": DEFAULT_USER_AGENT})
    resp.raise_for_status()
    html = resp.text

    if looks_like_js_shell(html, content_selector=content_selector):
        html = _render_with_playwright(url, timeout=timeout)

    if cache is not None:
        cache.put(url, html)

    return html
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_fetch.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add doctoskill/fetch.py tests/fixtures/sample_page.html tests/fixtures/js_shell.html tests/test_fetch.py
git commit -m "Add fetch layer with JS-shell detection, headless fallback, and caching"
```

---

### Task 11: Override config loader

**Files:**
- Create: `doctoskill/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `doctoskill.config.OverrideConfig` dataclass (`include: list[str]`, `exclude: list[str]`, `content_selector: str | None`, `nav_selector: str | None`), `doctoskill.config.load_config(path: str | None) -> OverrideConfig`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
import json

from doctoskill.config import OverrideConfig, load_config


def test_load_config_none_path_returns_defaults():
    config = load_config(None)
    assert config == OverrideConfig(include=[], exclude=[], content_selector=None, nav_selector=None)


def test_load_config_reads_json_file(tmp_path):
    config_path = tmp_path / "override.json"
    config_path.write_text(
        json.dumps(
            {
                "include": ["/docs/"],
                "exclude": ["/docs/changelog/"],
                "content_selector": "main.article-content",
                "nav_selector": "nav.sidebar",
            }
        ),
        encoding="utf-8",
    )
    config = load_config(str(config_path))
    assert config.include == ["/docs/"]
    assert config.exclude == ["/docs/changelog/"]
    assert config.content_selector == "main.article-content"
    assert config.nav_selector == "nav.sidebar"


def test_load_config_partial_file_keeps_other_defaults(tmp_path):
    config_path = tmp_path / "override.json"
    config_path.write_text(json.dumps({"content_selector": "main"}), encoding="utf-8")
    config = load_config(str(config_path))
    assert config.content_selector == "main"
    assert config.include == []
    assert config.nav_selector is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'doctoskill.config'`

- [ ] **Step 3: Write minimal implementation**

```python
# doctoskill/config.py
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class OverrideConfig:
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    content_selector: str | None = None
    nav_selector: str | None = None


def load_config(path: str | None) -> OverrideConfig:
    if not path:
        return OverrideConfig()
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return OverrideConfig(
        include=data.get("include", []),
        exclude=data.get("exclude", []),
        content_selector=data.get("content_selector"),
        nav_selector=data.get("nav_selector"),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add doctoskill/config.py tests/test_config.py
git commit -m "Add override config loader"
```

---

### Task 12: HTML-to-Markdown content conversion

**Files:**
- Create: `doctoskill/convert.py`
- Test: `tests/test_convert.py`

**Interfaces:**
- Produces: `doctoskill.convert.convert_page(html: str, content_selector: str | None = None) -> tuple[str, str]` (returns `(title, markdown)`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_convert.py
from pathlib import Path

from doctoskill.convert import convert_page

FIXTURES = Path(__file__).parent / "fixtures"


def test_convert_page_extracts_title_and_strips_boilerplate():
    html = (FIXTURES / "sample_page.html").read_text(encoding="utf-8")
    title, markdown = convert_page(html)
    assert title == "Sample Page Title"
    assert "Nav junk" not in markdown
    assert "Header junk" not in markdown
    assert "Footer junk" not in markdown
    assert "real content of the page" in markdown
    assert "print(\"hi\")" in markdown


def test_convert_page_respects_explicit_content_selector():
    html = (
        "<html><head><title>T</title></head><body>"
        "<nav>Nav</nav>"
        "<div class='article'><p>Only this should survive.</p></div>"
        "</body></html>"
    )
    title, markdown = convert_page(html, content_selector=".article")
    assert title == "T"
    assert "Nav" not in markdown
    assert "Only this should survive." in markdown


def test_convert_page_falls_back_to_h1_when_no_title_tag():
    html = "<html><body><main><h1>Fallback Title</h1><p>Body text.</p></main></body></html>"
    title, markdown = convert_page(html)
    assert title == "Fallback Title"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_convert.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'doctoskill.convert'`

- [ ] **Step 3: Write minimal implementation**

```python
# doctoskill/convert.py
from bs4 import BeautifulSoup
from markdownify import markdownify

CONTENT_SELECTOR_FALLBACKS = "main, article, [role=main], #content, .content"
BOILERPLATE_SELECTOR = "nav, header, footer, aside, script, style"


def _extract_title(soup: BeautifulSoup) -> str:
    if soup.title and soup.title.get_text(strip=True):
        return soup.title.get_text(strip=True)
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)
    return "Untitled"


def convert_page(html: str, content_selector: str | None = None) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = _extract_title(soup)

    if content_selector:
        content = soup.select_one(content_selector)
    else:
        content = soup.select_one(CONTENT_SELECTOR_FALLBACKS)
    if content is None:
        content = soup.body or soup

    for tag in content.select(BOILERPLATE_SELECTOR):
        tag.decompose()

    markdown = markdownify(str(content), heading_style="ATX").strip()
    return title, markdown
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_convert.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add doctoskill/convert.py tests/test_convert.py
git commit -m "Add HTML-to-Markdown content conversion"
```

---

### Task 13: Hierarchy resolution

**Files:**
- Create: `doctoskill/hierarchy.py`
- Test: `tests/test_hierarchy.py`

**Interfaces:**
- Consumes: `doctoskill.navtree.NavNode` (Task 6), `doctoskill.slugify.slugify` (Task 2), `doctoskill.urlutil.path_prefix` (Task 2).
- Produces: `doctoskill.hierarchy.flatten_navtree(node: NavNode) -> list[tuple[str, list[str], str]]` (returns `(url, path_segments, title)` tuples), `doctoskill.hierarchy.path_segments_from_url(url: str, base_url: str) -> list[str]`, `doctoskill.hierarchy.all_pages_flat(urls: list[str], base_url: str) -> bool`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_hierarchy.py
from doctoskill.hierarchy import all_pages_flat, flatten_navtree, path_segments_from_url
from doctoskill.navtree import NavNode


def test_flatten_navtree_matches_docfx_shape():
    tree = NavNode(
        title="root",
        url=None,
        children=[
            NavNode(
                title="Entities package",
                url="https://docs.example.com/manual/index.html",
                children=[
                    NavNode(title="What's new", url="https://docs.example.com/manual/whats-new.html", children=[]),
                ],
            ),
            NavNode(
                title="Get started",
                url="https://docs.example.com/manual/getting-started.html",
                children=[
                    NavNode(
                        title="ECS workflow examples",
                        url="https://docs.example.com/manual/ecs-workflow-tutorial.html",
                        children=[
                            NavNode(
                                title="Introduction",
                                url="https://docs.example.com/manual/ecs-workflow-intro.html",
                                children=[],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )

    entries = flatten_navtree(tree)
    by_url = {url: (segments, title) for url, segments, title in entries}

    assert by_url["https://docs.example.com/manual/index.html"] == ([], "Entities package")
    assert by_url["https://docs.example.com/manual/whats-new.html"] == (["entities-package"], "What's new")
    assert by_url["https://docs.example.com/manual/getting-started.html"] == ([], "Get started")
    assert by_url["https://docs.example.com/manual/ecs-workflow-intro.html"] == (
        ["get-started", "ecs-workflow-examples"],
        "Introduction",
    )


def test_path_segments_from_url_derives_from_directories():
    base_url = "https://example.com/docs/index.html"
    url = "https://example.com/docs/guide/setup/install.html"
    assert path_segments_from_url(url, base_url) == ["guide", "setup"]


def test_path_segments_from_url_flat_site_returns_empty():
    base_url = "https://example.com/manual/index.html"
    url = "https://example.com/manual/whats-new.html"
    assert path_segments_from_url(url, base_url) == []


def test_all_pages_flat_true_when_same_directory():
    base_url = "https://example.com/manual/index.html"
    urls = ["https://example.com/manual/index.html", "https://example.com/manual/whats-new.html"]
    assert all_pages_flat(urls, base_url) is True


def test_all_pages_flat_false_when_nested_directories():
    base_url = "https://example.com/docs/index.html"
    urls = ["https://example.com/docs/index.html", "https://example.com/docs/guide/setup.html"]
    assert all_pages_flat(urls, base_url) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_hierarchy.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'doctoskill.hierarchy'`

- [ ] **Step 3: Write minimal implementation**

```python
# doctoskill/hierarchy.py
from urllib.parse import urlsplit

from doctoskill.navtree import NavNode
from doctoskill.slugify import slugify
from doctoskill.urlutil import path_prefix


def flatten_navtree(node: NavNode, ancestors: list[str] | None = None) -> list[tuple[str, list[str], str]]:
    ancestors = ancestors or []
    entries: list[tuple[str, list[str], str]] = []
    for child in node.children:
        if child.url:
            entries.append((child.url, list(ancestors), child.title))
        if child.children:
            entries.extend(flatten_navtree(child, ancestors + [slugify(child.title)]))
    return entries


def path_segments_from_url(url: str, base_url: str) -> list[str]:
    base_dir = urlsplit(path_prefix(base_url)).path
    url_path = urlsplit(url).path
    if not url_path.startswith(base_dir):
        return []
    relative = url_path[len(base_dir):]
    segments = [segment for segment in relative.split("/") if segment][:-1]
    return [slugify(segment) for segment in segments]


def all_pages_flat(urls: list[str], base_url: str) -> bool:
    base_dir = urlsplit(path_prefix(base_url)).path
    return all(urlsplit(u).path.rsplit("/", 1)[0] + "/" == base_dir for u in urls)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_hierarchy.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add doctoskill/hierarchy.py tests/test_hierarchy.py
git commit -m "Add hierarchy resolution from nav-tree and URL structure"
```

---

### Task 14: SKILL.md generation and skill folder assembly

**Files:**
- Create: `doctoskill/skillmd.py`
- Create: `doctoskill/assemble.py`
- Test: `tests/test_skillmd.py`
- Test: `tests/test_assemble.py`

**Interfaces:**
- Consumes: `doctoskill.types.ConvertedPage` (Task 1).
- Produces: `doctoskill.skillmd.render_skill_md(name: str, description: str, overview: str, index_entries: list[tuple[str, str]]) -> str`, `doctoskill.assemble.assemble_skill(output_dir, skill_name: str, description: str, overview: str, pages: list[ConvertedPage]) -> Path`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_skillmd.py
from doctoskill.skillmd import render_skill_md


def test_render_skill_md_includes_frontmatter_and_index():
    markdown = render_skill_md(
        name="vuejs-docs",
        description="Vue.js framework documentation",
        overview="Vue.js is a progressive JavaScript framework.",
        index_entries=[("Getting Started", "references/getting-started.md")],
    )
    assert markdown.startswith("---\n")
    assert "name: vuejs-docs" in markdown
    assert "description: Vue.js framework documentation" in markdown
    assert "Vue.js is a progressive JavaScript framework." in markdown
    assert "[Getting Started](references/getting-started.md)" in markdown
```

```python
# tests/test_assemble.py
from doctoskill.assemble import assemble_skill
from doctoskill.types import ConvertedPage


def test_assemble_skill_writes_references_and_skill_md(tmp_path):
    pages = [
        ConvertedPage(title="Entities package", markdown="# Entities package\n\nOverview text.", path_segments=[]),
        ConvertedPage(title="What's new", markdown="# What's new\n\nChangelog.", path_segments=["entities-package"]),
    ]

    skill_dir = assemble_skill(
        tmp_path,
        skill_name="unity-entities-manual",
        description="Unity Entities package manual",
        overview="Documentation for the Unity Entities package.",
        pages=pages,
    )

    assert skill_dir == tmp_path / "unity-entities-manual"
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "references" / "entities-package.md").exists()
    assert (skill_dir / "references" / "entities-package" / "what-s-new.md").exists()

    skill_md = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert "references/entities-package.md" in skill_md
    assert "references/entities-package/what-s-new.md" in skill_md

    changelog = (skill_dir / "references" / "entities-package" / "what-s-new.md").read_text(encoding="utf-8")
    assert "Changelog." in changelog
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_skillmd.py tests/test_assemble.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'doctoskill.skillmd'`

- [ ] **Step 3: Write minimal implementation**

```python
# doctoskill/skillmd.py
def render_skill_md(name: str, description: str, overview: str, index_entries: list[tuple[str, str]]) -> str:
    frontmatter = f"---\nname: {name}\ndescription: {description}\n---\n\n"
    body = f"# {name}\n\n{overview}\n\n## Reference Index\n\n"
    for title, rel_path in index_entries:
        body += f"- [{title}]({rel_path})\n"
    return frontmatter + body
```

```python
# doctoskill/assemble.py
from pathlib import Path

from doctoskill.skillmd import render_skill_md
from doctoskill.slugify import slugify
from doctoskill.types import ConvertedPage


def assemble_skill(
    output_dir,
    skill_name: str,
    description: str,
    overview: str,
    pages: list[ConvertedPage],
) -> Path:
    skill_dir = Path(output_dir) / skill_name
    (skill_dir / "references").mkdir(parents=True, exist_ok=True)

    index_entries: list[tuple[str, str]] = []
    for page in pages:
        filename = f"{slugify(page.title)}.md"
        rel_path = "/".join(["references", *page.path_segments, filename])
        file_path = skill_dir / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(page.markdown + "\n", encoding="utf-8")
        index_entries.append((page.title, rel_path))

    skill_md = render_skill_md(skill_name, description, overview, index_entries)
    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

    return skill_dir
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_skillmd.py tests/test_assemble.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add doctoskill/skillmd.py doctoskill/assemble.py tests/test_skillmd.py tests/test_assemble.py
git commit -m "Add SKILL.md generation and skill folder assembly"
```

---

### Task 15: Zip packaging

**Files:**
- Create: `doctoskill/zippack.py`
- Test: `tests/test_zippack.py`

**Interfaces:**
- Produces: `doctoskill.zippack.zip_skill_folder(skill_dir, zip_path=None) -> Path`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_zippack.py
import zipfile

from doctoskill.zippack import zip_skill_folder


def test_zip_skill_folder_includes_files_and_excludes_cache(tmp_path):
    skill_dir = tmp_path / "my-skill"
    (skill_dir / "references").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("skill content", encoding="utf-8")
    (skill_dir / "references" / "page.md").write_text("page content", encoding="utf-8")
    (skill_dir / ".cache").mkdir()
    (skill_dir / ".cache" / "raw.html").write_text("cached html", encoding="utf-8")

    zip_path = zip_skill_folder(skill_dir)

    assert zip_path == skill_dir.with_suffix(".zip")
    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
    assert "SKILL.md" in names
    assert "references/page.md" in names
    assert not any(".cache" in name for name in names)


def test_zip_skill_folder_accepts_explicit_output_path(tmp_path):
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("skill content", encoding="utf-8")
    custom_path = tmp_path / "custom.zip"

    zip_path = zip_skill_folder(skill_dir, zip_path=custom_path)

    assert zip_path == custom_path
    assert custom_path.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_zippack.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'doctoskill.zippack'`

- [ ] **Step 3: Write minimal implementation**

```python
# doctoskill/zippack.py
import zipfile
from pathlib import Path


def zip_skill_folder(skill_dir, zip_path=None) -> Path:
    skill_dir = Path(skill_dir)
    zip_path = Path(zip_path) if zip_path else skill_dir.with_suffix(".zip")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in skill_dir.rglob("*"):
            if ".cache" in file_path.parts:
                continue
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(skill_dir))

    return zip_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_zippack.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add doctoskill/zippack.py tests/test_zippack.py
git commit -m "Add zip packaging for assembled skills"
```

---

### Task 16: CLI end-to-end wiring

**Files:**
- Modify: `doctoskill/cli.py`
- Test: `tests/test_cli_end_to_end.py`

**Interfaces:**
- Consumes: every module from Tasks 2-15 (`robots.can_crawl`, `llms_txt.{fetch_llms_txt, parse_llms_txt}`, `navtree_docfx.parse_docfx_toc`, `navtree_generic.parse_generic_navtree`, `sitemap.{fetch_sitemap_urls, filter_by_prefix}`, `crawler.crawl_path_prefix`, `cache.PageCache`, `fetch.fetch_page`, `config.load_config`, `hierarchy.{flatten_navtree, path_segments_from_url}`, `convert.convert_page`, `assemble.assemble_skill`, `zippack.zip_skill_folder`, `types.ConvertedPage`, `urlutil.path_prefix`, `slugify.slugify`).
- Produces: `doctoskill.cli.derive_skill_name(start_url: str) -> str`; updated `doctoskill.cli.main(argv=None) -> int` implementing the full pipeline described in the Global Constraints discovery order.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli_end_to_end.py
from pathlib import Path

import doctoskill.cli as cli_module
from doctoskill.navtree import NavNode


def test_derive_skill_name_slugifies_domain_and_path():
    name = cli_module.derive_skill_name("https://docs.example.com/manual/index.html")
    assert name == "docs-example-com-manual-index-html"


def test_main_uses_navtree_strategy_end_to_end(tmp_path, monkeypatch):
    start_url = "https://docs.example.com/manual/index.html"
    index_html = "<html><head><title>Entities package</title></head><body><main><h1>Entities package</h1><p>" + (
        "Overview content padded to be long enough to not look like a JS shell page for the detector heuristic used here."
    ) + "</p></main></body></html>"
    whats_new_html = "<html><head><title>What's new</title></head><body><main><h1>What's new</h1><p>" + (
        "Changelog content padded to be long enough to not look like a JS shell page for the detector heuristic used here."
    ) + "</p></main></body></html>"

    monkeypatch.setattr(cli_module, "can_crawl", lambda url: True)
    monkeypatch.setattr(cli_module, "fetch_llms_txt", lambda domain_root: None)

    tree = NavNode(
        title="root",
        url=None,
        children=[
            NavNode(title="Entities package", url=start_url, children=[
                NavNode(title="What's new", url="https://docs.example.com/manual/whats-new.html", children=[]),
            ]),
        ],
    )
    monkeypatch.setattr(cli_module, "parse_docfx_toc", lambda html, base_url: tree)

    pages_by_url = {
        "https://docs.example.com/manual/toc.html": "<html>toc placeholder</html>",
        start_url: index_html,
        "https://docs.example.com/manual/whats-new.html": whats_new_html,
    }
    monkeypatch.setattr(
        cli_module,
        "fetch_page",
        lambda url, cache=None, use_cache_only=False, content_selector=None: pages_by_url[url],
    )

    exit_code = cli_module.main(
        [start_url, "--output", str(tmp_path), "--name", "unity-entities-manual"]
    )

    assert exit_code == 0
    skill_dir = tmp_path / "unity-entities-manual"
    assert (skill_dir / "SKILL.md").exists()
    assert (skill_dir / "references" / "entities-package.md").exists()
    assert (skill_dir / "references" / "entities-package" / "what-s-new.md").exists()


def test_main_aborts_when_robots_disallows(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli_module, "can_crawl", lambda url: False)

    exit_code = cli_module.main(
        ["https://docs.example.com/manual/index.html", "--output", str(tmp_path)]
    )

    assert exit_code == 2
    assert not (tmp_path).exists() or not any((tmp_path).iterdir())
    captured = capsys.readouterr()
    assert "robots.txt" in captured.err
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli_end_to_end.py -v`
Expected: FAIL — `AttributeError: module 'doctoskill.cli' has no attribute 'derive_skill_name'`

- [ ] **Step 3: Write minimal implementation**

```python
# doctoskill/cli.py
import argparse
import sys
from pathlib import Path
from urllib.parse import urlsplit

from doctoskill.assemble import assemble_skill
from doctoskill.cache import PageCache
from doctoskill.config import load_config
from doctoskill.convert import convert_page
from doctoskill.crawler import crawl_path_prefix
from doctoskill.fetch import fetch_page
from doctoskill.hierarchy import flatten_navtree, path_segments_from_url
from doctoskill.llms_txt import fetch_llms_txt, parse_llms_txt
from doctoskill.navtree_docfx import parse_docfx_toc
from doctoskill.navtree_generic import parse_generic_navtree
from doctoskill.robots import can_crawl
from doctoskill.sitemap import fetch_sitemap_urls, filter_by_prefix
from doctoskill.slugify import slugify
from doctoskill.types import ConvertedPage
from doctoskill.urlutil import path_prefix
from doctoskill.zippack import zip_skill_folder


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="doctoskill",
        description="Convert a documentation website into an Agent Skill.",
    )
    parser.add_argument("start_url", help="First page of the docs to crawl")
    parser.add_argument("--output", default="./skills")
    parser.add_argument("--name", default=None)
    parser.add_argument("--max-pages", type=int, default=500)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--config", default=None)
    parser.add_argument("--skip-scrape", action="store_true")
    parser.add_argument("--zip", action="store_true")
    parser.add_argument("--enhance", action="store_true")
    return parser


def derive_skill_name(start_url: str) -> str:
    parts = urlsplit(start_url)
    return slugify(f"{parts.netloc}{parts.path}")


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    config = load_config(args.config)
    skill_name = args.name or derive_skill_name(args.start_url)

    if not can_crawl(args.start_url):
        print(f"robots.txt disallows crawling {args.start_url}", file=sys.stderr)
        return 2

    cache = PageCache(Path(args.output) / skill_name / ".cache")
    use_cache_only = args.skip_scrape
    if args.skip_scrape and not cache.has_any():
        print("Warning: --skip-scrape given but no cache found; performing a normal crawl.", file=sys.stderr)
        use_cache_only = False

    scheme_netloc = urlsplit(args.start_url)
    domain_root = f"{scheme_netloc.scheme}://{scheme_netloc.netloc}"

    pages: list[ConvertedPage] = []
    failed = 0
    strategy = None

    llms_text = fetch_llms_txt(domain_root)
    if llms_text:
        strategy = "llms.txt"
        for title, content in parse_llms_txt(llms_text):
            pages.append(ConvertedPage(title=title, markdown=content, path_segments=[]))
    else:
        discovered_urls: list[str] = []
        url_meta: dict[str, tuple[list[str], str]] = {}

        # DocFX renders its nav tree client-side from a sibling toc.html file,
        # not from markup embedded in the content page itself, so that file
        # has to be requested separately before falling back to a generic
        # inline-nav parse of the start page.
        toc_url = path_prefix(args.start_url) + "toc.html"
        try:
            toc_html = fetch_page(
                toc_url, cache=cache, use_cache_only=use_cache_only, content_selector=config.content_selector
            )
        except Exception:
            toc_html = None

        navtree = None
        if toc_html:
            navtree = parse_docfx_toc(toc_html, args.start_url)

        if navtree is None:
            try:
                index_html = fetch_page(
                    args.start_url,
                    cache=cache,
                    use_cache_only=use_cache_only,
                    content_selector=config.content_selector,
                )
            except Exception:
                index_html = None
            if index_html:
                navtree = parse_generic_navtree(index_html, args.start_url, nav_selector=config.nav_selector)

        if navtree is not None:
            strategy = "nav-tree"
            entries = flatten_navtree(navtree)
            discovered_urls = [url for url, _segments, _title in entries]
            url_meta = {url: (segments, title) for url, segments, title in entries}
        else:
            prefix = path_prefix(args.start_url)
            sitemap_urls = fetch_sitemap_urls(domain_root)
            filtered = filter_by_prefix(sitemap_urls, prefix) if sitemap_urls else []
            if config.include:
                filtered = [u for u in filtered if any(fragment in u for fragment in config.include)]

            if filtered:
                strategy = "sitemap"
                discovered_urls = filtered
            else:
                strategy = "path-prefix-crawl"
                discovered_urls = crawl_path_prefix(args.start_url, max_pages=args.max_pages, delay=args.delay)

        if config.exclude:
            discovered_urls = [u for u in discovered_urls if not any(fragment in u for fragment in config.exclude)]

        for url in discovered_urls[: args.max_pages]:
            try:
                html = fetch_page(
                    url, cache=cache, use_cache_only=use_cache_only, content_selector=config.content_selector
                )
            except Exception:
                failed += 1
                continue
            try:
                title, markdown = convert_page(html, content_selector=config.content_selector)
            except Exception:
                failed += 1
                continue

            if url in url_meta:
                segments, nav_title = url_meta[url]
                title = nav_title or title
            else:
                segments = path_segments_from_url(url, args.start_url)

            pages.append(ConvertedPage(title=title, markdown=markdown, path_segments=segments, url=url))

    description = f"Documentation for {skill_name}, scraped from {args.start_url}."
    overview = f"This skill contains documentation scraped from {args.start_url}."
    skill_dir = assemble_skill(Path(args.output), skill_name, description, overview, pages)

    if args.zip:
        zip_skill_folder(skill_dir)

    print(f"Strategy: {strategy}")
    print(f"Pages converted: {len(pages)}")
    print(f"Pages failed: {failed}")
    print(f"Skill written to: {skill_dir}")
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli_end_to_end.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run the full test suite to confirm nothing regressed**

Run: `pytest -v`
Expected: All tests PASS (Tasks 1-16 combined)

- [ ] **Step 6: Commit**

```bash
git add doctoskill/cli.py tests/test_cli_end_to_end.py
git commit -m "Wire discovery, fetch, convert, and assemble into the CLI pipeline"
```

---

### Task 17 (optional): `--enhance` LLM polish pass

**Files:**
- Create: `doctoskill/enhance.py`
- Modify: `doctoskill/cli.py`
- Test: `tests/test_enhance.py`
- Modify: `tests/test_cli_end_to_end.py`

**Interfaces:**
- Consumes: assembled skill folder path from `assemble_skill` (Task 14).
- Produces: `doctoskill.enhance.enhance_skill(skill_dir, client=None) -> None`.

This task is independent of the core pipeline (Tasks 1-16 already produce a complete, working tool) and requires an `ANTHROPIC_API_KEY` to exercise for real. Implement it last, and only if `--enhance` is wanted for this iteration.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_enhance.py
from doctoskill.enhance import enhance_skill


class FakeMessage:
    def __init__(self, text):
        self.content = [type("Block", (), {"text": text})()]


class FakeMessages:
    def __init__(self, response_text):
        self.response_text = response_text
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return FakeMessage(self.response_text)


class FakeClient:
    def __init__(self, response_text):
        self.messages = FakeMessages(response_text)


def test_enhance_skill_rewrites_skill_md(tmp_path):
    skill_dir = tmp_path / "my-skill"
    (skill_dir / "references").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: old description\n---\n\nOld overview.\n",
        encoding="utf-8",
    )
    (skill_dir / "references" / "intro.md").write_text("# Intro\n\nSome content.", encoding="utf-8")

    client = FakeClient("---\nname: my-skill\ndescription: improved description\n---\n\nImproved overview.\n")
    enhance_skill(skill_dir, client=client)

    result = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert result == "---\nname: my-skill\ndescription: improved description\n---\n\nImproved overview.\n"
    assert client.messages.last_kwargs["model"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_enhance.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'doctoskill.enhance'`

- [ ] **Step 3: Write minimal implementation**

```python
# doctoskill/enhance.py
from pathlib import Path

MODEL = "claude-sonnet-5"


def enhance_skill(skill_dir, client=None) -> None:
    skill_dir = Path(skill_dir)
    skill_md_path = skill_dir / "SKILL.md"
    current_skill_md = skill_md_path.read_text(encoding="utf-8")

    reference_snippets = []
    for reference_file in sorted((skill_dir / "references").rglob("*.md")):
        reference_snippets.append(reference_file.read_text(encoding="utf-8")[:2000])

    if client is None:
        import anthropic

        client = anthropic.Anthropic()

    prompt = (
        "Rewrite the following SKILL.md to have a sharper overview and a better "
        "description, using the reference excerpts for context. Keep the same "
        "YAML frontmatter keys (name, description) and the Reference Index section "
        "unchanged. Return only the full replacement SKILL.md content.\n\n"
        f"Current SKILL.md:\n{current_skill_md}\n\n"
        f"Reference excerpts:\n{'---'.join(reference_snippets)}"
    )

    message = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    new_skill_md = message.content[0].text
    skill_md_path.write_text(new_skill_md, encoding="utf-8")
```

Then wire it into `cli.py` by adding this import near the other module imports:

```python
from doctoskill.enhance import enhance_skill
```

and adding this block in `main()` immediately after the `if args.zip:` block:

```python
    if args.enhance:
        enhance_skill(skill_dir)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_enhance.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Run the full test suite to confirm nothing regressed**

Run: `pytest -v`
Expected: All tests PASS (Tasks 1-17 combined)

- [ ] **Step 6: Commit**

```bash
git add doctoskill/enhance.py doctoskill/cli.py tests/test_enhance.py
git commit -m "Add optional --enhance LLM polish pass for SKILL.md"
```
