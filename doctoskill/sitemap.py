import xml.etree.ElementTree as ET
from typing import Optional

import requests

from doctoskill.robots import DEFAULT_USER_AGENT
from doctoskill.urlutil import is_under_prefix


def _fetch_xml(url: str, session, timeout: float) -> Optional[ET.Element]:
    try:
        response = session.get(url, timeout=timeout)
    except Exception:
        return None
    if response.status_code >= 400 or not response.text.strip():
        return None
    try:
        return ET.fromstring(response.text)
    except ET.ParseError:
        return None


def fetch_sitemap_urls(domain_root: str, session=None, timeout: float = 10.0) -> Optional[list[str]]:
    """Fetch sitemap.xml, including one level of sitemap-index expansion."""
    session = session or requests
    root = _fetch_xml(f"{domain_root.rstrip('/')}/sitemap.xml", session, timeout)
    if root is None:
        return None
    locations = [
        element.text.strip()
        for element in root.iter()
        if element.tag.endswith("loc") and element.text and element.text.strip()
    ]
    if root.tag.endswith("sitemapindex"):
        urls: list[str] = []
        for sitemap_url in locations:
            child = _fetch_xml(sitemap_url, session, timeout)
            if child is not None:
                urls.extend(
                    element.text.strip()
                    for element in child.iter()
                    if element.tag.endswith("loc") and element.text and element.text.strip()
                )
        return list(dict.fromkeys(urls)) or None
    return list(dict.fromkeys(locations)) or None


def filter_by_prefix(urls: list[str], prefix: str) -> list[str]:
    return [url for url in urls if is_under_prefix(url, prefix)]
