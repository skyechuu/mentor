import re
from typing import Iterable, Optional
from urllib.parse import unquote, urlsplit

from doctoskill.slugify import slugify
from doctoskill.types import ConvertedPage

UNITY_PACKAGE_RE = re.compile(
    r"/Packages/com\.unity\.([^@/]+)@([^/]+)",
    re.IGNORECASE,
)
VERSION_RE = re.compile(r"(?<!\d)v?(\d+(?:\.\d+)+(?:[-a-z0-9.]*)?)", re.IGNORECASE)
MARKDOWN_HEADING_RE = re.compile(r"^#{1,3}\s+(.+?)\s*$", re.MULTILINE)
GENERIC_TOPICS = {
    "api",
    "documentation",
    "docs",
    "get started",
    "getting started",
    "guide",
    "home",
    "index",
    "introduction",
    "manual",
    "overview",
    "reference",
    "table of contents",
    "untitled",
    "what s new",
}


def _safe_version(value: str) -> str:
    return re.sub(r"[^a-z0-9.-]+", "-", value.lower()).strip("-.")


def _normalize_requested_name(value: str) -> str:
    value = re.sub(r"[^a-z0-9.-]+", "-", value.strip().lower())
    value = re.sub(r"-{2,}", "-", value).strip("-.")
    return value or "documentation"


def _unity_product(start_url: str) -> Optional[tuple[str, str, str]]:
    match = UNITY_PACKAGE_RE.search(unquote(urlsplit(start_url).path))
    if not match:
        return None
    package = match.group(1).replace(".", "-")
    version = _safe_version(match.group(2))
    name = f"unity-{slugify(package)}-{version}"
    label = f"Unity {package.replace('-', ' ').title()} (ECS/DOTS) {version}"
    return name, label, version


def _clean_product_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title).strip()
    title = re.split(r"\s+[|–—]\s+", title, maxsplit=1)[0]
    title = re.sub(
        r"\s+(?:documentation|docs|manual|reference)(?:\s+home)?$",
        "",
        title,
        flags=re.IGNORECASE,
    )
    return title.strip() or "Documentation"


def derive_skill_name(start_url: str, product_title: Optional[str] = None) -> str:
    """Derive a concise product-version name, preserving version dots."""
    unity = _unity_product(start_url)
    if unity:
        return unity[0]

    parts = urlsplit(start_url)
    title = _clean_product_title(product_title) if product_title else ""
    if not title:
        host_parts = [part for part in parts.hostname.split(".") if part] if parts.hostname else []
        host_parts = [part for part in host_parts if part not in {"www", "docs", "documentation", "com", "org", "net"}]
        title = host_parts[0] if host_parts else "documentation"

    name = slugify(title)
    version_match = VERSION_RE.search(unquote(parts.path))
    if version_match:
        version = _safe_version(version_match.group(1))
        if version and version not in name:
            name = f"{name}-{version}"
    return name


def _topic_candidates(pages: Iterable[ConvertedPage]) -> Iterable[str]:
    for page in pages:
        yield page.title
    for page in pages:
        yield from MARKDOWN_HEADING_RE.findall(page.markdown)


def extract_topics(pages: list[ConvertedPage], product_label: str, limit: int = 14) -> list[str]:
    topics: list[str] = []
    seen: set[str] = set()
    product_words = set(slugify(product_label).split("-"))
    for candidate in _topic_candidates(pages):
        candidate = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", candidate)
        candidate = re.sub(r"[`*_#]", "", candidate)
        candidate = re.sub(r"\s+", " ", candidate).strip(" :-–—")
        key = slugify(candidate).replace("-", " ")
        if not candidate or len(candidate) > 64 or key in GENERIC_TOPICS or key in seen:
            continue
        candidate_words = set(slugify(candidate).split("-"))
        if candidate_words and candidate_words <= product_words:
            continue
        seen.add(key)
        topics.append(candidate)
        if len(topics) >= limit:
            break
    return topics


def build_skill_metadata(
    start_url: str,
    pages: list[ConvertedPage],
    requested_name: Optional[str] = None,
) -> tuple[str, str, str]:
    """Return a useful skill name, trigger description, and overview."""
    first_title = pages[0].title if pages else "Documentation"
    unity = _unity_product(start_url)
    if unity:
        derived_name, product_label, _version = unity
        product_description = f"Complete {product_label} documentation"
    else:
        product_label = _clean_product_title(first_title)
        derived_name = derive_skill_name(start_url, product_label)
        product_description = f"Complete {product_label} documentation"

    name = _normalize_requested_name(requested_name) if requested_name else derived_name

    topics = extract_topics(pages, product_label)
    if topics:
        trigger = ", ".join(topics)
        description = (
            f"{product_description}. Use for {trigger}. "
            "Open only relevant reference files."
        )
    else:
        description = (
            f"{product_description}. Use for questions and implementation work involving "
            f"{product_label}. Open only relevant reference files."
        )
    overview = (
        f"Use this skill for {product_label}. Start with the reference index and open only "
        "the files relevant to the current question."
    )
    return name, description, overview
