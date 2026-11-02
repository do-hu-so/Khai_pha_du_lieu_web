"""Crawler HTML tổng quát - "focused crawler" theo cấu hình trong config/sources.yaml.

Chiến lược: 2 hàng đợi
  - article_queue: URL bài viết  -> tải, trích xuất nội dung, lưu
  - listing_queue: URL danh mục  -> tải, chỉ lấy link
Luôn ưu tiên xử lý bài viết trước, hết bài mới mở thêm trang danh mục (duyệt BFS).
Hỗ trợ chạy tiếp (resume): URL đã thăm được ghi vào visited.txt.
"""
from __future__ import annotations

import hashlib
import logging
import re
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup

from ..utils.io import append_jsonl, read_jsonl
from .extract import body_classes, extract_article
from .http import PoliteSession

log = logging.getLogger(__name__)


def doc_id_from_url(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


class HtmlSiteCrawler:
    def __init__(self, cfg: dict, session: PoliteSession, out_dir: Path):
        self.cfg = cfg
        self.session = session
        self.out_dir = out_dir
        self.docs_file = out_dir / "documents.jsonl"
        self.visited_file = out_dir / "visited.txt"
        self.article_re = re.compile(cfg["article_url_regex"]) if cfg.get("article_url_regex") else None
        self.follow_re = re.compile(cfg["follow_url_regex"]) if cfg.get("follow_url_regex") else None
        self.deny_re = re.compile(cfg["deny_url_regex"]) if cfg.get("deny_url_regex") else None
        # Nhận diện bài viết theo class của <body> (WordPress): có ít nhất 1 class "any", không có class "none"
        body_rule = cfg.get("article_body_class") or {}
        self.body_any = set(body_rule.get("any", []))
        self.body_none = set(body_rule.get("none", []))
        self.title_strip = re.compile(cfg["title_strip_regex"]) if cfg.get("title_strip_regex") else None
        self.hosts = {urlparse(u).netloc.replace("www.", "") for u in cfg["start_urls"]}

    # ---------------- phân loại URL ----------------
    def _normalize(self, base: str, href: str) -> str | None:
        if not href or href.startswith(("mailto:", "javascript:", "tel:")):
            return None
        url, _ = urldefrag(urljoin(base, href.strip()))
        p = urlparse(url)
        if p.scheme not in ("http", "https") or p.netloc.replace("www.", "") not in self.hosts:
            return None
        if re.search(r"\.(jpg|jpeg|png|gif|webp|svg|pdf|mp3|mp4|zip|rar|doc|docx|css|js)(\?|$)", p.path, re.I):
            return None
        return url

    def _is_denied(self, url: str) -> bool:
        return bool(self.deny_re and self.deny_re.search(url))

    def _is_article_url(self, url: str) -> bool:
        return bool(self.article_re and self.article_re.match(url))

    def _is_follow_url(self, url: str) -> bool:
        return bool(self.follow_re and self.follow_re.match(url))

    def _is_article_page(self, html: str) -> bool:
        if not self.body_any:
            return False
        classes = body_classes(html)
        return bool(classes & self.body_any) and not (classes & self.body_none)

    # ---------------- vòng lặp chính ----------------
    def run(self) -> int:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        saved_urls = {d["url"] for d in read_jsonl(self.docs_file)}
        visited = set(self.visited_file.read_text(encoding="utf-8").split()) if self.visited_file.exists() else set()
        max_articles = int(self.cfg["max_articles"])
        max_pages = int(self.cfg["max_pages"])
        n_saved, n_requests = len(saved_urls), 0
        if n_saved >= max_articles:
            log.info("[%s] đã đủ %d bài (bỏ qua). Dùng --fresh để crawl lại.", self.cfg["id"], n_saved)
            return 0

        article_q: deque[str] = deque()
        listing_q: deque[str] = deque(self.cfg["start_urls"])
        queued = set(listing_q)
        new_docs = 0
        visited_fh = open(self.visited_file, "a", encoding="utf-8")
        try:
            while (article_q or listing_q) and n_saved < max_articles and n_requests < max_pages:
                url = article_q.popleft() if article_q else listing_q.popleft()
                # Khi chạy tiếp: trang danh mục vẫn mở lại để lấy link; bài viết đã thử thì bỏ qua
                if url in saved_urls or (url in visited and self._is_article_url(url)):
                    continue
                resp = self.session.get(url)
                n_requests += 1
                visited.add(url)
                visited_fh.write(url + "\n")
                if resp is None or "html" not in resp.headers.get("Content-Type", "html"):
                    continue
                html = resp.text

                if self._is_article_url(url) or self._is_article_page(html):
                    doc = extract_article(html, url)
                    if doc and len(doc["text"]) >= 200:
                        if self.title_strip:
                            doc["title"] = self.title_strip.sub("", doc["title"]).strip()
                        record = {
                            "id": doc_id_from_url(url),
                            "source": self.cfg["id"],
                            "source_name": self.cfg["name"],
                            "url": url,
                            **doc,
                            "crawled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        }
                        append_jsonl(self.docs_file, record)
                        saved_urls.add(url)
                        n_saved += 1
                        new_docs += 1
                        if new_docs % 25 == 0:
                            log.info("[%s] đã lưu %d/%d bài (%d request)", self.cfg["id"], n_saved, max_articles, n_requests)

                # Thu thập link mới
                soup = BeautifulSoup(html, "lxml")
                for a in soup.find_all("a", href=True):
                    link = self._normalize(url, a["href"])
                    if not link or link in queued or self._is_denied(link):
                        continue
                    if self._is_article_url(link):
                        article_q.append(link)
                        queued.add(link)
                    elif self._is_follow_url(link):
                        listing_q.append(link)
                        queued.add(link)
        finally:
            visited_fh.close()
        log.info("[%s] HOÀN TẤT: +%d bài mới, tổng %d bài, %d request", self.cfg["id"], new_docs, n_saved, n_requests)
        return new_docs
