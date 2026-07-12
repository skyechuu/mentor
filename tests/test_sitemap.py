from doctoskill.sitemap import fetch_sitemap_urls, filter_by_prefix


class Response:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code


class Session:
    def __init__(self, values):
        self.values = values

    def get(self, url, timeout=10):
        return Response(self.values.get(url, ""), 200 if url in self.values else 404)


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
