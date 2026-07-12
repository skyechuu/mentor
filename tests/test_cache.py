from doctoskill.cache import PageCache, cache_dir_for


def test_cache_roundtrip_and_url_index(tmp_path):
    cache = PageCache(tmp_path / "cache")
    assert not cache.has_any()
    assert cache.get("https://example.com/missing") is None
    cache.put("https://example.com/a", "<html>A</html>")
    assert cache.get("https://example.com/a") == "<html>A</html>"
    assert cache.has_any()
    assert cache.urls() == ["https://example.com/a"]


def test_generated_cache_is_outside_output_directory(tmp_path):
    output = tmp_path / "skills"
    cache_dir = cache_dir_for(output, "https://example.com/docs/")
    assert output not in cache_dir.parents
    assert cache_dir.parent.parent.name == ".doctoskill-cache"
