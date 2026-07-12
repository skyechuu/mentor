from bs4 import BeautifulSoup
from typing import Optional

from doctoskill.robots import DEFAULT_USER_AGENT

CONTENT_SELECTOR_FALLBACKS = "main, article, [role=main], #content, .content"


class CacheMissError(Exception):
    """Raised when cache-only fetching cannot find a URL."""


class HeadlessBrowserUnavailable(RuntimeError):
    """Raised when a JS shell requires the optional Playwright dependency."""


def looks_like_js_shell(
    html: str,
    content_selector: Optional[str] = None,
    min_length: int = 200,
) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    if content_selector:
        element = soup.select_one(content_selector)
        if element is None:
            return True
    else:
        element = soup.select_one(CONTENT_SELECTOR_FALLBACKS) or soup.body
    text = element.get_text(" ", strip=True) if element else ""
    if len(text) >= min_length:
        return False
    # A short page is not necessarily a JS shell. Require a script plus a
    # common empty application mount when no explicit selector was supplied.
    if content_selector:
        return True
    has_script = soup.find("script", src=True) is not None
    app_mount = soup.select_one("#root, #app, #__next, [data-reactroot]")
    mount_text = app_mount.get_text(" ", strip=True) if app_mount else ""
    return has_script and app_mount is not None and not mount_text


def _render_with_playwright(url: str, timeout: float = 10.0) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise HeadlessBrowserUnavailable(
            "Page appears to require JavaScript. Install doctoskill[playwright] "
            "and run `playwright install chromium`."
        ) from exc

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(url, timeout=timeout * 1000, wait_until="networkidle")
            return page.content()
        finally:
            browser.close()


def fetch_page(
    url: str,
    cache=None,
    use_cache_only: bool = False,
    content_selector: Optional[str] = None,
    session=None,
    timeout: float = 10.0,
) -> str:
    if cache is not None:
        cached = cache.get(url)
        if cached is not None:
            return cached
        if use_cache_only:
            raise CacheMissError(url)

    if session is None:
        import requests

        session = requests
    response = session.get(
        url,
        timeout=timeout,
        headers={"User-Agent": DEFAULT_USER_AGENT},
    )
    response.raise_for_status()
    html = response.text

    if looks_like_js_shell(html, content_selector=content_selector):
        html = _render_with_playwright(url, timeout=timeout)
    if cache is not None:
        cache.put(url, html)
    return html
