from bs4 import BeautifulSoup
from typing import Optional

from doctoskill.navtree import NavNode, iter_nodes
from doctoskill.urlutil import is_under_prefix, path_prefix, resolve_link

MIN_LINKS = 3


def _walk(ul) -> list[NavNode]:
    nodes: list[NavNode] = []
    for li in ul.find_all("li", recursive=False):
        anchor = li.find("a", recursive=False)
        if anchor is None:
            continue
        child_ul = li.find("ul", recursive=False)
        nodes.append(
            NavNode(
                title=anchor.get_text(" ", strip=True) or anchor.get("title") or "Untitled",
                url=anchor.get("href"),
                children=_walk(child_ul) if child_ul is not None else [],
            )
        )
    return nodes


def _in_scope_link_count(ul, base_url: str) -> int:
    prefix = path_prefix(base_url)
    count = 0
    for anchor in ul.find_all("a", href=True):
        url = resolve_link(base_url, anchor.get("href"))
        if url and is_under_prefix(url, prefix):
            count += 1
    return count


def _prune_out_of_scope(nodes: list[NavNode], base_url: str) -> list[NavNode]:
    prefix = path_prefix(base_url)
    kept: list[NavNode] = []
    for node in nodes:
        node.children = _prune_out_of_scope(node.children, base_url)
        in_scope = bool(node.url and is_under_prefix(node.url, prefix))
        if in_scope:
            kept.append(node)
        elif node.children:
            node.url = None
            kept.append(node)
    return kept


def parse_generic_navtree(
    html: str,
    base_url: str,
    nav_selector: Optional[str] = None,
) -> Optional[NavNode]:
    soup = BeautifulSoup(html, "html.parser")
    if nav_selector:
        candidates = [soup.select_one(nav_selector)]
        minimum = 1
    else:
        candidates = soup.select(
            "nav, [class*=sidebar], [class*=side-nav], [class*=toc], [class*=menu]"
        )
        minimum = MIN_LINKS

    best_ul = None
    best_count = 0
    for candidate in candidates:
        if candidate is None:
            continue
        ul = candidate if candidate.name == "ul" else candidate.find("ul")
        if ul is None:
            continue
        count = (
            len(ul.find_all("a", href=True))
            if nav_selector
            else _in_scope_link_count(ul, base_url)
        )
        if count > best_count:
            best_ul, best_count = ul, count

    if best_ul is None or best_count < minimum:
        return None
    root = NavNode(title="root", url=None, children=_walk(best_ul))
    if not root.children:
        return None
    for node in iter_nodes(root):
        if node.url:
            node.url = resolve_link(base_url, node.url)
    if not nav_selector:
        root.children = _prune_out_of_scope(root.children, base_url)
        if not root.children:
            return None
    return root
