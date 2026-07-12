from doctoskill.hierarchy import all_pages_flat, flatten_navtree, path_segments_from_url
from doctoskill.navtree import NavNode


def test_flatten_navtree_uses_display_hierarchy():
    tree = NavNode(
        "root",
        None,
        [NavNode("Guide", "https://example.com/manual/index.html", [NavNode("Start", "https://example.com/manual/start.html")])],
    )
    assert flatten_navtree(tree) == [
        ("https://example.com/manual/index.html", [], "Guide"),
        ("https://example.com/manual/start.html", ["guide"], "Start"),
    ]


def test_url_hierarchy_and_flat_detection():
    base = "https://example.com/docs/index.html"
    assert path_segments_from_url(
        "https://example.com/docs/guide/setup/install.html", base
    ) == ["guide", "setup"]
    assert all_pages_flat(
        [base, "https://example.com/docs/start.html"], base
    )
    assert not all_pages_flat(
        [base, "https://example.com/docs/guide/start.html"], base
    )
