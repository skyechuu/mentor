from doctoskill.crawler import crawl_path_prefix

PAGES = {
    "https://example.com/docs/index.html": (
        '<a href="a.html">A</a><a href="b.html">B</a>'
        '<a href="https://example.com/blog/post">Blog</a>'
    ),
    "https://example.com/docs/a.html": '<a href="c.html">C</a>',
    "https://example.com/docs/b.html": '<a href="index.html">Home</a>',
    "https://example.com/docs/c.html": "",
}


def test_bfs_crawl_stays_in_scope_and_respects_limit():
    order = crawl_path_prefix(
        "https://example.com/docs/index.html",
        fetch_fn=PAGES.__getitem__,
        sleep_fn=lambda _seconds: None,
    )
    assert order == [
        "https://example.com/docs/index.html",
        "https://example.com/docs/a.html",
        "https://example.com/docs/b.html",
        "https://example.com/docs/c.html",
    ]
    assert len(
        crawl_path_prefix(
            "https://example.com/docs/index.html",
            max_pages=2,
            fetch_fn=PAGES.__getitem__,
            sleep_fn=lambda _seconds: None,
        )
    ) == 2


def test_crawl_skips_disallowed_pages():
    order = crawl_path_prefix(
        "https://example.com/docs/index.html",
        fetch_fn=PAGES.__getitem__,
        sleep_fn=lambda _seconds: None,
        allowed_fn=lambda url: not url.endswith("a.html"),
    )
    assert "https://example.com/docs/a.html" not in order
    assert "https://example.com/docs/c.html" not in order


def test_crawl_reports_live_progress():
    messages = []
    crawl_path_prefix(
        "https://example.com/docs/index.html",
        max_pages=2,
        fetch_fn=PAGES.__getitem__,
        sleep_fn=lambda _seconds: None,
        progress_fn=messages.append,
    )
    assert messages[0] == (
        "Crawling page 1/2: https://example.com/docs/index.html"
    )
    assert messages[1].startswith("Crawling page 2/2:")


def test_crawl_follows_article_links_not_global_navigation():
    pages = {
        "https://example.com/manual/ui.html": """
          <header><a href='index.html'>Whole manual</a></header>
          <div class='content'><a href='index.html'>Global menu</a></div>
          <div class='section'><h1>UI</h1>
            <a href='visual-elements.html'>Visual elements</a>
            <a href='events.html'>Events</a>
          </div>
        """,
        "https://example.com/manual/visual-elements.html": "<h1>Visual elements</h1>",
        "https://example.com/manual/events.html": "<h1>Events</h1>",
    }
    order = crawl_path_prefix(
        "https://example.com/manual/ui.html",
        fetch_fn=pages.__getitem__,
        sleep_fn=lambda _seconds: None,
    )
    assert order == [
        "https://example.com/manual/ui.html",
        "https://example.com/manual/visual-elements.html",
        "https://example.com/manual/events.html",
    ]
