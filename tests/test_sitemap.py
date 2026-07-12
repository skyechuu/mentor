from doctoskill.sitemap import fetch_sitemap_urls, filter_by_prefix


class Response:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code


class StreamingResponse:
    def __init__(self, chunks, status_code=200):
        self.chunks = chunks
        self.status_code = status_code
        self.headers = {}
        self.encoding = "utf-8"
        self.closed = False

    def iter_content(self, chunk_size=65536):
        yield from self.chunks

    def close(self):
        self.closed = True


class Session:
    def __init__(self, values):
        self.values = values

        self.calls = []

    def get(self, url, timeout=10, **kwargs):
        self.calls.append(url)
        if url not in self.values:
            return Response("", 404)
        value = self.values[url]
        return value if hasattr(value, "status_code") else Response(value)


def test_sitemap_parse_filter_and_missing():
    xml = """<?xml version='1.0'?><urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>
    <url><loc>https://example.com/docs/intro</loc></url>
    <url><loc>https://example.com/blog/post</loc></url></urlset>"""
    urls = fetch_sitemap_urls(
        "https://example.com",
        session=Session({"https://example.com/sitemap.xml": xml}),
    )
    assert urls == ["https://example.com/docs/intro", "https://example.com/blog/post"]
    assert filter_by_prefix(urls, "https://example.com/docs/") == urls[:1]
    assert fetch_sitemap_urls("https://example.com", session=Session({})) is None


def test_sitemap_index_expands_child_maps():
    index = "<sitemapindex><sitemap><loc>https://example.com/docs.xml</loc></sitemap></sitemapindex>"
    child = "<urlset><url><loc>https://example.com/docs/a</loc></url></urlset>"
    session = Session(
        {"https://example.com/sitemap.xml": index, "https://example.com/docs.xml": child}
    )
    assert fetch_sitemap_urls("https://example.com", session=session) == [
        "https://example.com/docs/a"
    ]


def test_sitemap_filters_during_expansion_and_stops_at_limit():
    index = """<sitemapindex>
      <sitemap><loc>https://example.com/one.xml</loc></sitemap>
      <sitemap><loc>https://example.com/two.xml</loc></sitemap>
    </sitemapindex>"""
    one = """<urlset>
      <url><loc>https://example.com/blog/a</loc></url>
      <url><loc>https://example.com/docs/a</loc></url>
      <url><loc>https://example.com/docs/b</loc></url>
    </urlset>"""
    session = Session(
        {
            "https://example.com/sitemap.xml": index,
            "https://example.com/one.xml": one,
            "https://example.com/two.xml": "<urlset/>",
        }
    )
    urls = fetch_sitemap_urls(
        "https://example.com",
        session=session,
        prefix="https://example.com/docs/",
        max_urls=1,
    )
    assert urls == ["https://example.com/docs/a"]
    assert "https://example.com/two.xml" not in session.calls


def test_sitemap_index_skips_large_children_and_reports_progress():
    child_urls = [f"https://example.com/child-{index}.xml" for index in range(5)]
    index = "<sitemapindex>" + "".join(
        f"<sitemap><loc>{url}</loc></sitemap>" for url in child_urls
    ) + "</sitemapindex>"
    streaming_responses = {
        url: StreamingResponse([b"<urlset>", b"x" * 1000, b"</urlset>"])
        for url in child_urls
    }
    session = Session(
        {"https://example.com/sitemap.xml": index, **streaming_responses}
    )
    messages = []
    urls = fetch_sitemap_urls(
        "https://example.com",
        session=session,
        max_bytes=600,
        max_child_sitemaps=2,
        progress_fn=messages.append,
    )
    assert urls is None
    assert session.calls == [
        "https://example.com/sitemap.xml",
        child_urls[0],
        child_urls[1],
    ]
    assert all(streaming_responses[url].closed for url in child_urls[:2])
    assert any("lists 5 child maps" in message for message in messages)
    assert sum("oversized child" in message for message in messages) == 2
