from dataclasses import dataclass
from typing import Optional


@dataclass
class ConvertedPage:
    title: str
    markdown: str
    path_segments: list[str]
    url: Optional[str] = None
