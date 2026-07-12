from bs4 import BeautifulSoup
from typing import Optional

from doctoskill.navtree import NavNode, iter_nodes
from doctoskill.urlutil import resolve_link


def _walk(ul) -> list[NavNode]:
    nodes: list[NavNode] = []
    for li in ul.find_all("li", recursive=False):
        anchor = li.find("a", recursive=False)
        if anchor is None:
            continue
        title = anchor.get("title") or anchor.get_text(" ", strip=True)
        child_ul = li.find("ul", recursive=False)
        nodes.append(
            NavNode(
                title=title,
                url=anchor.get("href"),
                children=_walk(child_ul) if child_ul is not None else [],
            )
        )
    return nodes


def parse_docfx_toc(html: str, base_url: str) -> Optional[NavNode]:
    soup = BeautifulSoup(html, "html.parser")
    top_ul = soup.select_one("div#toc ul.nav, #sidetoggle .toc ul.nav, ul.nav.level1")
    if top_ul is None:
        return None
    root = NavNode(title="root", url=None, children=_walk(top_ul))
    if not root.children:
        return None
    for node in iter_nodes(root):
        if node.url:
            node.url = resolve_link(base_url, node.url)
    return root
