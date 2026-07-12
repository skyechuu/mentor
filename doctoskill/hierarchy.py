from urllib.parse import unquote, urlsplit
from typing import Optional

from doctoskill.navtree import NavNode
from doctoskill.slugify import slugify
from doctoskill.urlutil import path_prefix


def flatten_navtree(
    node: NavNode,
    ancestors: Optional[list[str]] = None,
) -> list[tuple[str, list[str], str]]:
    ancestors = ancestors or []
    entries: list[tuple[str, list[str], str]] = []
    for child in node.children:
        if child.url:
            entries.append((child.url, list(ancestors), child.title))
        if child.children:
            entries.extend(flatten_navtree(child, ancestors + [slugify(child.title)]))
    return entries


def path_segments_from_url(url: str, base_url: str) -> list[str]:
    base_dir = urlsplit(path_prefix(base_url)).path
    url_path = urlsplit(url).path
    if not url_path.startswith(base_dir):
        return []
    relative = url_path[len(base_dir) :]
    directories = [segment for segment in relative.split("/") if segment][:-1]
    return [slugify(unquote(segment)) for segment in directories]


def all_pages_flat(urls: list[str], base_url: str) -> bool:
    base_dir = urlsplit(path_prefix(base_url)).path
    return all(urlsplit(url).path.rsplit("/", 1)[0] + "/" == base_dir for url in urls)
