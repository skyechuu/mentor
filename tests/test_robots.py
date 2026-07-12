from doctoskill.robots import can_crawl


class FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code


class FakeSession:
    def __init__(self, text=None, error=None, status_code=200):
        self.text = text
        self.error = error
        self.status_code = status_code

    def get(self, url, timeout=10, headers=None):
        if self.error:
            raise self.error
        return FakeResponse(self.text, self.status_code)


def test_robots_disallow_and_allow():
    session = FakeSession("User-agent: *\nDisallow: /manual/\n")
    assert not can_crawl("https://example.com/manual/index.html", session=session)
    assert can_crawl("https://example.com/other/index.html", session=session)


def test_missing_robots_is_allowed():
    assert can_crawl(
        "https://example.com/manual/index.html",
        session=FakeSession(error=ConnectionError("offline")),
    )
    assert can_crawl(
        "https://example.com/manual/index.html",
        session=FakeSession("", status_code=404),
    )
