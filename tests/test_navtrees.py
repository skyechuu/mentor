from doctoskill.navtree_docfx import parse_docfx_toc
from doctoskill.navtree_generic import parse_generic_navtree

BASE = "https://example.com/manual/index.html"


def test_docfx_navtree_parser():
    html = """<div id='toc'><ul class='nav level1'>
      <li><a href='index.html' title='Manual'>Manual</a><ul class='nav level2'>
        <li><a href='start.html' title='Start'>Start</a></li></ul></li>
      <li><a href='api.html'>API</a></li></ul></div>"""
    root = parse_docfx_toc(html, BASE)
    assert root is not None
    assert [node.title for node in root.children] == ["Manual", "API"]
    assert root.children[0].children[0].url == "https://example.com/manual/start.html"
    assert parse_docfx_toc("<p>none</p>", BASE) is None


def test_generic_navtree_and_explicit_selector():
    html = """<nav class='sidebar'><ul>
      <li><a href='intro.html'>Intro</a></li>
      <li><a href='setup.html'>Setup</a><ul><li><a href='install.html'>Install</a></li></ul></li>
      <li><a href='api.html'>API</a></li></ul></nav>"""
    root = parse_generic_navtree(html, BASE)
    assert root is not None
    assert [node.title for node in root.children] == ["Intro", "Setup", "API"]
    assert root.children[1].children[0].title == "Install"
    explicit = parse_generic_navtree(
        "<div id='menu'><ul><li><a href='/one'>One</a></li></ul></div>",
        BASE,
        "#menu",
    )
    assert explicit is not None
    assert explicit.children[0].title == "One"
