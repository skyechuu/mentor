import hashlib
import json
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

from doctoskill.slugify import slugify


def _cache_dir_for_root(output_dir, start_url: str, root_name: str) -> Path:
    output_path = Path(output_dir).resolve()
    digest = hashlib.sha256(start_url.encode("utf-8")).hexdigest()[:16]
    host = slugify(urlsplit(start_url).netloc)
    return output_path.parent / root_name / slugify(output_path.name) / f"{host}-{digest}"


def cache_dir_for(output_dir, start_url: str) -> Path:
    """Return Mentor's crawl cache outside the generated output directory."""
    return _cache_dir_for_root(output_dir, start_url, ".mentor-cache")


def legacy_cache_dir_for(output_dir, start_url: str) -> Path:
    """Return the pre-Mentor cache path for one-time migration."""
    return _cache_dir_for_root(output_dir, start_url, ".doctoskill-cache")


class PageCache:
    """Raw HTML cache with a small URL index for offline reruns."""

    INDEX_FILENAME = "index.json"

    def __init__(self, cache_dir):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.html"

    @property
    def _index_path(self) -> Path:
        return self.cache_dir / self.INDEX_FILENAME

    def _read_index(self) -> dict[str, str]:
        try:
            data = json.loads(self._index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def get(self, url: str) -> Optional[str]:
        path = self._path_for(url)
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None

    def put(self, url: str, html: str) -> None:
        path = self._path_for(url)
        path.write_text(html, encoding="utf-8")
        index = self._read_index()
        index[url] = path.name
        self._index_path.write_text(
            json.dumps(index, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def has_any(self) -> bool:
        return any(self.cache_dir.glob("*.html"))

    def urls(self) -> list[str]:
        index = self._read_index()
        return sorted(url for url, filename in index.items() if (self.cache_dir / filename).exists())
