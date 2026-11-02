"""HTTP client "lịch sự": tôn trọng robots.txt, giãn cách request theo host, tự retry."""
from __future__ import annotations

import logging
import threading
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

log = logging.getLogger(__name__)


class PoliteSession:
    def __init__(
        self,
        user_agent: str,
        delay_seconds: float = 1.0,
        timeout_seconds: float = 30,
        max_retries: int = 3,
        respect_robots: bool = True,
    ):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept-Language": "vi,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        })
        self.user_agent = user_agent
        self.delay = delay_seconds
        self.timeout = timeout_seconds
        self.max_retries = max_retries
        self.respect_robots = respect_robots
        self._robots: dict[str, RobotFileParser | None] = {}
        self._last_request: dict[str, float] = {}
        self._lock = threading.Lock()

    # ---------------- robots.txt ----------------
    def can_fetch(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        p = urlparse(url)
        host = f"{p.scheme}://{p.netloc}"
        if host not in self._robots:
            rp = RobotFileParser()
            try:
                r = self.session.get(host + "/robots.txt", timeout=self.timeout)
                if r.status_code == 200 and "user-agent" in r.text.lower():
                    rp.parse(r.text.splitlines())
                    self._robots[host] = rp
                else:  # không có robots.txt hợp lệ -> cho phép
                    self._robots[host] = None
            except requests.RequestException:
                self._robots[host] = None
        rp = self._robots[host]
        return True if rp is None else rp.can_fetch(self.user_agent, url)

    # ---------------- request ----------------
    def _wait(self, url: str) -> None:
        host = urlparse(url).netloc
        with self._lock:
            elapsed = time.time() - self._last_request.get(host, 0)
            if elapsed < self.delay:
                time.sleep(self.delay - elapsed)
            self._last_request[host] = time.time()

    def request(self, method: str, url: str, **kwargs) -> requests.Response | None:
        if not self.can_fetch(url):
            log.debug("robots.txt chặn: %s", url)
            return None
        for attempt in range(1, self.max_retries + 1):
            self._wait(url)
            try:
                r = self.session.request(method, url, timeout=self.timeout, **kwargs)
                if r.status_code == 200:
                    if not r.encoding or r.encoding.lower() == "iso-8859-1":
                        r.encoding = r.apparent_encoding or "utf-8"
                    return r
                if r.status_code in (403, 404, 410):
                    log.debug("HTTP %s: %s", r.status_code, url)
                    return None
                log.warning("HTTP %s (lần %d): %s", r.status_code, attempt, url)
            except requests.RequestException as e:
                log.warning("Lỗi mạng (lần %d) %s: %s", attempt, url, e)
            time.sleep(2 ** attempt)
        return None

    def get(self, url: str, **kwargs) -> requests.Response | None:
        return self.request("GET", url, **kwargs)

    def post_json(self, url: str, payload: dict) -> requests.Response | None:
        return self.request("POST", url, json=payload)
