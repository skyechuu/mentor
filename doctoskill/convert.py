import re
from typing import Optional

from bs4 import BeautifulSoup
from markdownify import markdownify

from doctoskill.content import select_content

BOILERPLATE_SELECTOR = (
    "nav, header, footer, aside, script, style, noscript, form, "
    "[aria-hidden=true], .advertisement, .ads, .cookie-banner"
)
DOCFX_TOC_TOGGLE_RE = re.compile(
    r"^\s*(?:\[)?Show\s*/\s*Hide Table of Contents(?:\])?"
    r"(?:\([^\n]*sidetoggle[^\n]*\))?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _extract_title(soup: BeautifulSoup) -> str:
    h1 = soup.find("h1")
    if h1 and h1.get_text(" ", strip=True):
        return h1.get_text(" ", strip=True)
    if soup.title and soup.title.get_text(" ", strip=True):
        return soup.title.get_text(" ", strip=True)
    return "Untitled"


def convert_page(html: str, content_selector: Optional[str] = None) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = _extract_title(soup)
    content = select_content(soup, content_selector)
    if content is None:
        content = soup.body or soup
    for tag in content.select(BOILERPLATE_SELECTOR):
        tag.decompose()
    markdown = markdownify(str(content), heading_style="ATX").strip()
    markdown = DOCFX_TOC_TOGGLE_RE.sub("", markdown)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return title, markdown
