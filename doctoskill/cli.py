import argparse
import shutil
import sys
from pathlib import Path
from urllib.parse import urlsplit
from typing import Optional

from doctoskill.assemble import assemble_skill
from doctoskill.cache import PageCache, cache_dir_for
from doctoskill.config import load_config
from doctoskill.convert import convert_page
from doctoskill.crawler import crawl_path_prefix
from doctoskill.fetch import fetch_page
from doctoskill.hierarchy import flatten_navtree, path_segments_from_url
from doctoskill.llms_txt import fetch_llms_txt, parse_llms_txt
from doctoskill.metadata import build_skill_metadata, derive_skill_name
from doctoskill.navtree_docfx import parse_docfx_toc
from doctoskill.navtree_generic import parse_generic_navtree
from doctoskill.robots import can_crawl
from doctoskill.sitemap import fetch_sitemap_urls, filter_by_prefix
from doctoskill.slugify import slugify
from doctoskill.types import ConvertedPage
from doctoskill.urlutil import domain_root, is_under_prefix, path_prefix
from doctoskill.zippack import zip_skill_folder


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="doctoskill",
        description="Convert a documentation website into an Agent Skill.",
    )
    parser.add_argument("start_url", help="First page of the docs to crawl")
    parser.add_argument("--output", default="./skills", help="Parent output directory")
    parser.add_argument("--name", default=None, help="Skill name (derived from URL by default)")
    parser.add_argument("--max-pages", type=int, default=500, help="Maximum pages to convert")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between crawl requests")
    parser.add_argument("--config", default=None, help="JSON override config")
    parser.add_argument("--skip-scrape", action="store_true", help="Use cached pages only")
    parser.add_argument("--zip", action="store_true", help="Also write a .zip package")
    parser.add_argument("--enhance", action="store_true", help="Polish SKILL.md with Anthropic")
    return parser


def _matches_config(url: str, include: list[str], exclude: list[str]) -> bool:
    if include and not any(fragment in url for fragment in include):
        return False
    return not any(fragment in url for fragment in exclude)


def _fetch_for_crawl(url: str, cache: PageCache, content_selector: Optional[str]) -> str:
    return fetch_page(url, cache=cache, content_selector=content_selector)


def _discover_from_navtree(
    start_url: str,
    cache: PageCache,
    use_cache_only: bool,
    content_selector: Optional[str],
    nav_selector: Optional[str],
):
    toc_url = path_prefix(start_url) + "toc.html"
    try:
        toc_html = fetch_page(
            toc_url,
            cache=cache,
            use_cache_only=use_cache_only,
            content_selector=content_selector,
        )
    except Exception:
        toc_html = None
    navtree = parse_docfx_toc(toc_html, start_url) if toc_html else None
    if navtree is not None:
        return navtree

    try:
        index_html = fetch_page(
            start_url,
            cache=cache,
            use_cache_only=use_cache_only,
            content_selector=content_selector,
        )
    except Exception:
        return None
    return parse_generic_navtree(index_html, start_url, nav_selector=nav_selector)


def _validate_args(parser: argparse.ArgumentParser, args) -> None:
    parts = urlsplit(args.start_url)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        parser.error("start_url must be an absolute http(s) URL")
    if args.max_pages < 1:
        parser.error("--max-pages must be at least 1")
    if args.delay < 0:
        parser.error("--delay cannot be negative")


def _prepare_cache(output_dir, start_url: str, legacy_skill_names: list[str]) -> PageCache:
    """Use the external cache location and migrate pre-0.2 in-skill caches."""
    output_path = Path(output_dir)
    cache_dir = cache_dir_for(output_path, start_url)
    for legacy_skill_name in dict.fromkeys(legacy_skill_names):
        legacy_dir = output_path / legacy_skill_name / ".cache"
        if legacy_dir.exists():
            cache_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(legacy_dir, cache_dir, dirs_exist_ok=True)
            shutil.rmtree(legacy_dir)
    return PageCache(cache_dir)


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    _validate_args(parser, args)

    try:
        config = load_config(args.config)
    except (OSError, ValueError) as exc:
        print(f"Invalid config: {exc}", file=sys.stderr)
        return 2

    url_parts = urlsplit(args.start_url)
    old_url_slug_name = slugify(f"{url_parts.netloc}{url_parts.path}")
    legacy_skill_names = [args.name or derive_skill_name(args.start_url), old_url_slug_name]
    if not can_crawl(args.start_url):
        print(f"robots.txt disallows crawling {args.start_url}", file=sys.stderr)
        return 2

    cache = _prepare_cache(args.output, args.start_url, legacy_skill_names)
    use_cache_only = args.skip_scrape and cache.has_any()
    if args.skip_scrape and not use_cache_only:
        print(
            "Warning: --skip-scrape given but no cache found; performing a normal crawl.",
            file=sys.stderr,
        )

    pages: list[ConvertedPage] = []
    failed = 0
    found = 0
    strategy: Optional[str] = None

    # Cache-only mode never contacts discovery endpoints. A cached nav tree is
    # preferred; otherwise the URL index supplies the previous page set.
    navtree = None
    if use_cache_only:
        navtree = _discover_from_navtree(
            args.start_url,
            cache,
            True,
            config.content_selector,
            config.nav_selector,
        )
        llms_text = None
    else:
        llms_text = fetch_llms_txt(domain_root(args.start_url))

    llms_sections = parse_llms_txt(llms_text) if llms_text else []
    if llms_sections:
        strategy = "llms.txt"
        found = len(llms_sections)
        for title, content in llms_sections[: args.max_pages]:
            pages.append(ConvertedPage(title=title, markdown=content, path_segments=[]))
    else:
        if navtree is None:
            navtree = _discover_from_navtree(
                args.start_url,
                cache,
                use_cache_only,
                config.content_selector,
                config.nav_selector,
            )

        discovered_urls: list[str] = []
        url_meta: dict[str, tuple[list[str], str]] = {}
        if navtree is not None:
            strategy = "nav-tree"
            entries = flatten_navtree(navtree)
            discovered_urls = [url for url, _segments, _title in entries]
            url_meta = {url: (segments, title) for url, segments, title in entries}
        elif use_cache_only:
            strategy = "cache"
            prefix = path_prefix(args.start_url)
            toc_url = prefix + "toc.html"
            discovered_urls = [
                url for url in cache.urls() if url != toc_url and is_under_prefix(url, prefix)
            ]
        else:
            prefix = path_prefix(args.start_url)
            sitemap_urls = fetch_sitemap_urls(domain_root(args.start_url))
            filtered = filter_by_prefix(sitemap_urls, prefix) if sitemap_urls else []
            if filtered:
                strategy = "sitemap"
                discovered_urls = filtered
            else:
                strategy = "path-prefix-crawl"
                discovered_urls = crawl_path_prefix(
                    args.start_url,
                    max_pages=args.max_pages,
                    delay=args.delay,
                    fetch_fn=lambda url: _fetch_for_crawl(url, cache, config.content_selector),
                )

        discovered_urls = list(
            dict.fromkeys(
                url
                for url in discovered_urls
                if _matches_config(url, config.include, config.exclude)
            )
        )[: args.max_pages]
        found = len(discovered_urls)

        for url in discovered_urls:
            try:
                html = fetch_page(
                    url,
                    cache=cache,
                    use_cache_only=use_cache_only,
                    content_selector=config.content_selector,
                )
                title, markdown = convert_page(html, content_selector=config.content_selector)
                if not markdown.strip():
                    raise ValueError("converted page was empty")
            except Exception as exc:
                failed += 1
                print(f"Warning: skipped {url}: {exc}", file=sys.stderr)
                continue

            if url in url_meta:
                segments, nav_title = url_meta[url]
                title = nav_title or title
            else:
                segments = path_segments_from_url(url, args.start_url)
            pages.append(ConvertedPage(title, markdown, segments, url))

    if not pages:
        print("No documentation pages could be converted.", file=sys.stderr)
        return 1

    skill_name, description, overview = build_skill_metadata(
        args.start_url,
        pages,
        requested_name=args.name,
    )
    skill_dir = assemble_skill(args.output, skill_name, description, overview, pages)

    if args.enhance:
        try:
            from doctoskill.enhance import enhance_skill

            enhance_skill(skill_dir)
        except Exception as exc:
            print(f"Enhancement failed: {exc}", file=sys.stderr)
            return 1
    if args.zip:
        zip_skill_folder(skill_dir)

    print(f"Strategy: {strategy}")
    print(f"Pages found: {found}")
    print(f"Pages converted: {len(pages)}")
    print(f"Pages skipped/failed: {failed}")
    print(f"Skill written to: {skill_dir}")
    return 0
