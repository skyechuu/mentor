import urllib.robotparser as robotparser
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit
from typing import Optional

import requests

DEFAULT_USER_AGENT = "DocToSkillBot/0.1"


@dataclass
class RobotsPolicy:
    parser: Optional[robotparser.RobotFileParser] = None

    def can_fetch(self, url: str) -> bool:
        return self.parser is None or self.parser.can_fetch(DEFAULT_USER_AGENT, url)


def fetch_robots_policy(start_url: str, session=None, timeout: float = 10.0) -> RobotsPolicy:
    parts = urlsplit(start_url)
    robots_url = urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))
    session = session or requests
    try:
        response = session.get(
            robots_url,
            timeout=timeout,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )
        if response.status_code >= 400:
            return RobotsPolicy()
    except Exception:
        return RobotsPolicy()

    parser = robotparser.RobotFileParser()
    parser.set_url(robots_url)
    parser.parse(response.text.splitlines())
    return RobotsPolicy(parser)


def can_crawl(start_url: str, session=None, timeout: float = 10.0) -> bool:
    return fetch_robots_policy(start_url, session=session, timeout=timeout).can_fetch(start_url)
