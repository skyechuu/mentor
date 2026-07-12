import re
from typing import Optional

from bs4 import BeautifulSoup

ARTICLE_CLASS_PATTERNS = (
    re.compile(r"^(?:article|documentation|manual-content|page-content)$", re.I),
    re.compile(r"^(?:content-body|article-content|doc-content)$", re.I),
    re.compile(r"^section$", re.I),
    re.compile(r"^content$", re.I),
)


def select_content(soup: BeautifulSoup, content_selector: Optional[str] = None):
    """Select article content while avoiding unrelated elements named content."""
    if content_selector:
        return soup.select_one(content_selector)

    for selector in ("main", "article", "[role=main]", "#content"):
        element = soup.select_one(selector)
        if element is not None:
            return element

    heading = soup.find("h1")
    if heading is not None:
        ancestors = [parent for parent in heading.parents if getattr(parent, "name", None)]
        for pattern in ARTICLE_CLASS_PATTERNS:
            for ancestor in ancestors:
                classes = ancestor.get("class", [])
                if any(pattern.search(class_name) for class_name in classes):
                    return ancestor

    return soup.body or soup
