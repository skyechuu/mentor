import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class OverrideConfig:
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    content_selector: Optional[str] = None
    nav_selector: Optional[str] = None


def _string_list(data: dict, key: str) -> list[str]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"config field {key!r} must be a list of strings")
    return value


def load_config(path: Optional[str]) -> OverrideConfig:
    if not path:
        return OverrideConfig()
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("config root must be a JSON object")
    for key in ("content_selector", "nav_selector"):
        if key in data and data[key] is not None and not isinstance(data[key], str):
            raise ValueError(f"config field {key!r} must be a string")
    return OverrideConfig(
        include=_string_list(data, "include"),
        exclude=_string_list(data, "exclude"),
        content_selector=data.get("content_selector"),
        nav_selector=data.get("nav_selector"),
    )
