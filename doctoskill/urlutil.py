from urllib.parse import urljoin, urlsplit, urlunsplit
from typing import Optional


def _origin(url: str) -> tuple[str, str]:
    parts = urlsplit(url)
    return parts.scheme.lower(), parts.netloc.lower()


def same_domain(url_a: str, url_b: str) -> bool:
    return urlsplit(url_a).netloc.lower() == urlsplit(url_b).netloc.lower()


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url)
    path = parts.path or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def domain_root(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, "", "", ""))


def path_prefix(url: str) -> str:
    parts = urlsplit(url)
    path = parts.path or "/"
    if not path.endswith("/"):
        path = path.rsplit("/", 1)[0] + "/"
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def is_under_prefix(url: str, prefix: str) -> bool:
    candidate = urlsplit(url)
    root = urlsplit(prefix)
    return _origin(url) == _origin(prefix) and candidate.path.startswith(root.path)


def resolve_link(base_url: str, href: Optional[str]) -> Optional[str]:
    if not href:
        return None
    href = href.strip()
    if not href or href.lower().startswith(("mailto:", "javascript:", "tel:", "data:")):
        return None
    resolved = canonicalize_url(urljoin(base_url, href))
    if urlsplit(resolved).scheme not in ("http", "https"):
        return None
    return resolved
