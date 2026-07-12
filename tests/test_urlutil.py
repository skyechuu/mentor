from doctoskill.urlutil import is_under_prefix, path_prefix, resolve_link, same_domain


def test_url_scope_helpers():
    prefix = path_prefix("https://docs.example.com/manual/index.html")
    assert prefix == "https://docs.example.com/manual/"
    assert same_domain(prefix, "https://docs.example.com/other")
    assert not same_domain(prefix, "https://other.example.com/manual/")
    assert is_under_prefix("https://docs.example.com/manual/new.html", prefix)
    assert not is_under_prefix("https://docs.example.com/manuality/new.html", prefix)
    assert not is_under_prefix("https://evil.example/manual/new.html", prefix)


def test_resolve_link_normalizes_and_rejects_non_web_links():
    base = "https://docs.example.com/manual/index.html"
    assert resolve_link(base, "whats-new.html#section") == (
        "https://docs.example.com/manual/whats-new.html"
    )
    assert resolve_link(base, "mailto:a@example.com") is None
    assert resolve_link(base, None) is None
