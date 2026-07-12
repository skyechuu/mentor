import pytest

import doctoskill.fetch as fetch_module
from doctoskill.cache import PageCache
from doctoskill.fetch import CacheMissError, fetch_page, looks_like_js_shell

RENDERED = """<html><head><title>Page</title></head><body><main><h1>Page</h1><p>
This is rendered documentation content and it is deliberately padded so that the
shell detector recognizes it as a complete server-rendered page with useful text.
Additional documentation text makes the content comfortably longer than the configured threshold.
</p></main></body></html>"""
SHELL = "<html><body><div id='root'></div><script src='/app.js'></script></body></html>"


class Response:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


class Session:
    def __init__(self, text):
        self.text = text
        self.calls = 0

    def get(self, url, timeout=10, headers=None):
        self.calls += 1
        return Response(self.text)


def test_js_shell_detection_distinguishes_short_static_page():
    assert not looks_like_js_shell(RENDERED)
    assert looks_like_js_shell(SHELL)
    assert not looks_like_js_shell("<html><body><main>Short static page.</main></body></html>")


def test_fetch_direct_headless_and_cache(monkeypatch, tmp_path):
    assert fetch_page("https://example.com/page", session=Session(RENDERED)) == RENDERED
    monkeypatch.setattr(fetch_module, "_render_with_playwright", lambda url, timeout=10: RENDERED)
    assert fetch_page("https://example.com/app", session=Session(SHELL)) == RENDERED

    cache = PageCache(tmp_path / "cache")
    session = Session(RENDERED)
    assert fetch_page("https://example.com/page", session=session, cache=cache) == RENDERED
    assert fetch_page("https://example.com/page", session=session, cache=cache) == RENDERED
    assert session.calls == 1


def test_cache_only_miss(tmp_path):
    with pytest.raises(CacheMissError):
        fetch_page(
            "https://example.com/missing",
            cache=PageCache(tmp_path / "cache"),
            use_cache_only=True,
        )
