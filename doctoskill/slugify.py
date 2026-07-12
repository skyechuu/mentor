import re
import unicodedata


def slugify(text: str) -> str:
    """Return a filesystem-friendly, deterministic ASCII slug."""
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    normalized = normalized.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    return normalized.strip("-") or "untitled"
