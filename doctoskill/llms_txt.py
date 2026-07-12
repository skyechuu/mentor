import re
from typing import Optional

import requests

from doctoskill.robots import DEFAULT_USER_AGENT

CANDIDATE_FILES = ("llms-full.txt", "llms.txt")


def fetch_llms_txt(domain_root: str, session=None, timeout: float = 10.0) -> Optional[str]:
    session = session or requests
    base = domain_root.rstrip("/")
    for filename in CANDIDATE_FILES:
        try:
            response = session.get(
                f"{base}/{filename}",
                timeout=timeout,
                headers={"User-Agent": DEFAULT_USER_AGENT},
            )
        except Exception:
            continue
        if response.status_code < 400 and response.text.strip():
            return response.text
    return None


def parse_llms_txt(text: str) -> list[tuple[str, str]]:
    """Split a full llms.txt document on level-two headings."""
    sections: list[tuple[str, str]] = []
    title: Optional[str] = None
    body: list[str] = []
    in_fence = False

    for line in text.splitlines():
        if re.match(r"^\s*(```|~~~)", line):
            in_fence = not in_fence
        if not in_fence and line.startswith("## "):
            if title is not None:
                sections.append((title, "\n".join(body).strip()))
            title = line[3:].strip()
            body = []
        elif title is not None:
            body.append(line)

    if title is not None:
        sections.append((title, "\n".join(body).strip()))
    return [(heading, content) for heading, content in sections if content]
