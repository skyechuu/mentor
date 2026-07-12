import doctoskill.cli as cli_module
from doctoskill.cache import PageCache
from doctoskill.navtree import NavNode


def _page(title, text):
    return f"<html><head><title>{title}</title></head><body><main><h1>{title}</h1><p>{text}</p></main></body></html>"


def test_derive_skill_name():
    assert cli_module.derive_skill_name(
        "https://docs.unity3d.com/Packages/com.unity.entities@6.5/manual/index.html"
    ) == "unity-entities-6.5"


def test_main_navtree_end_to_end(tmp_path, monkeypatch):
    start = "https://docs.example.com/manual/index.html"
    child = "https://docs.example.com/manual/whats-new.html"
    tree = NavNode(
        "root",
        None,
        [NavNode("Entities package", start, [NavNode("What's new", child)])],
    )
    pages = {
        "https://docs.example.com/manual/toc.html": "<div>toc</div>",
        start: _page("Entities package", "Overview content."),
        child: _page("What's new", "Changelog content."),
    }
    monkeypatch.setattr(cli_module, "can_crawl", lambda url: True)
    monkeypatch.setattr(cli_module, "fetch_llms_txt", lambda root: None)
    monkeypatch.setattr(cli_module, "parse_docfx_toc", lambda html, base: tree)
    monkeypatch.setattr(
        cli_module,
        "fetch_page",
        lambda url, cache=None, use_cache_only=False, content_selector=None: pages[url],
    )

    result = cli_module.main(
        [start, "--output", str(tmp_path), "--name", "unity-entities", "--zip"]
    )
    assert result == 0
    skill = tmp_path / "unity-entities"
    assert (skill / "SKILL.md").exists()
    assert (skill / "references" / "entities-package.md").exists()
    assert (skill / "references" / "entities-package" / "what-s-new.md").exists()
    assert (tmp_path / "unity-entities.zip").exists()


def test_main_uses_llms_txt_without_page_fetches(tmp_path, monkeypatch):
    monkeypatch.setattr(cli_module, "can_crawl", lambda url: True)
    monkeypatch.setattr(
        cli_module,
        "fetch_llms_txt",
        lambda root: "# Docs\n\n## Start\n\nStart here.\n\n## API\n\nAPI docs.",
    )
    monkeypatch.setattr(
        cli_module,
        "fetch_page",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not fetch HTML")),
    )
    assert cli_module.main(
        ["https://example.com/docs/index.html", "--output", str(tmp_path), "--name", "docs"]
    ) == 0
    assert (tmp_path / "docs" / "references" / "start.md").exists()


def test_skip_scrape_uses_cache_without_discovery_network(tmp_path, monkeypatch):
    start = "https://example.com/manual/index.html"
    child = "https://example.com/manual/start.html"
    cache = PageCache(tmp_path / "cached-skill" / ".cache")
    cache.put(
        "https://example.com/manual/toc.html",
        "<div id='toc'><ul class='nav'><li><a href='index.html'>Manual</a><ul><li><a href='start.html'>Start</a></li></ul></li></ul></div>",
    )
    cache.put(start, _page("Manual", "Manual overview."))
    cache.put(child, _page("Start", "Start instructions."))
    monkeypatch.setattr(cli_module, "can_crawl", lambda url: True)
    monkeypatch.setattr(
        cli_module,
        "fetch_llms_txt",
        lambda root: (_ for _ in ()).throw(AssertionError("must not discover online")),
    )
    assert cli_module.main(
        [
            start,
            "--output",
            str(tmp_path),
            "--name",
            "cached-skill",
            "--skip-scrape",
        ]
    ) == 0
    assert (tmp_path / "cached-skill" / "references" / "manual" / "start.md").exists()


def test_main_aborts_for_robots(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli_module, "can_crawl", lambda url: False)
    assert cli_module.main(
        ["https://example.com/manual/index.html", "--output", str(tmp_path)]
    ) == 2
    assert "robots.txt" in capsys.readouterr().err
    assert not tmp_path.exists() or not any(tmp_path.iterdir())
