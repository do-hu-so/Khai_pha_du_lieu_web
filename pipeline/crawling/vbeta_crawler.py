"""Crawler cho vbeta.vn - Thư viện số hóa kinh sách Phật giáo.

vbeta.vn là ứng dụng Angular (SPA) nên HTML không chứa nội dung. Dữ liệu được lấy
qua API công khai mà chính website sử dụng (https://api.phapbao.org/api):
  - search/get-books-by-categoryId        : danh sách sách theo thể loại (Kinh/Luật/Luận/Sách)
  - search/get-tableofcontents-selectlist-by-bookid/{bookId} : mục lục của sách
  - search/get-pages-by-tableofcontentid/{tocId}             : nội dung (HTML) của 1 mục
Mỗi mục lục (chương/bài kinh) được lưu thành 1 văn bản.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from ..utils.io import append_jsonl, read_jsonl
from .extract import html_to_text
from .http import PoliteSession

log = logging.getLogger(__name__)


class VbetaCrawler:
    def __init__(self, cfg: dict, session: PoliteSession, out_dir: Path):
        self.cfg = cfg
        self.session = session
        self.api = cfg["api_root"].rstrip("/")
        self.web = cfg["web_root"].rstrip("/")
        self.out_dir = out_dir
        self.docs_file = out_dir / "documents.jsonl"

    def _get(self, path: str):
        r = self.session.get(f"{self.api}/{path}")
        return r.json().get("result") if r is not None else None

    def _post(self, path: str, payload: dict):
        r = self.session.post_json(f"{self.api}/{path}", payload)
        return r.json().get("result") if r is not None else None

    def _books(self, category_id: int, limit: int) -> list[dict]:
        books, skip = [], 0
        while len(books) < limit:
            res = self._post("search/get-books-by-categoryId", {"id": category_id, "skip": skip, "take": 16})
            if not res or not res.get("items"):
                break
            books.extend(res["items"])
            if not res.get("hasMore"):
                break
            skip += 1  # API phân trang theo chỉ số trang
        return books[:limit]

    def run(self) -> int:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        done = {d["id"] for d in read_jsonl(self.docs_file)}
        skip_re = re.compile(self.cfg["skip_toc_regex"], re.IGNORECASE) if self.cfg.get("skip_toc_regex") else None
        min_chars = int(self.cfg.get("min_chars", 200))
        max_total = int(self.cfg["max_articles"])
        n_new = 0
        for cat_id in self.cfg["category_ids"]:
            if len(done) >= max_total:
                break
            books = self._books(cat_id, int(self.cfg["max_books_per_category"]))
            log.info("[vbeta] thể loại %s: %d sách", cat_id, len(books))
            for book in books:
                if len(done) >= max_total:
                    break
                tocs = self._get(f"search/get-tableofcontents-selectlist-by-bookid/{book['id']}") or []
                if skip_re:  # bỏ các mục không phải nội dung kinh văn (Ban chứng minh, Hội đồng ...)
                    tocs = [t for t in tocs if not skip_re.search(t["label"])]
                for toc in tocs[: int(self.cfg["max_chapters_per_book"])]:
                    doc_id = f"vbeta-{book['id']}-{toc['value']}"
                    if doc_id in done:
                        continue
                    if len(done) >= max_total:
                        break
                    res = self._get(f"search/get-pages-by-tableofcontentid/{toc['value']}")
                    if not res or not res.get("pages"):
                        continue
                    html = "\n".join(p.get("htmlContent") or "" for p in sorted(res["pages"], key=lambda p: p.get("sortNumber", 0)))
                    text = html_to_text(html)
                    if len(text) < min_chars:
                        continue
                    seo = toc.get("seoName") or res.get("seoName") or "muc-luc"
                    append_jsonl(self.docs_file, {
                        "id": doc_id,
                        "source": self.cfg["id"],
                        "source_name": self.cfg["name"],
                        "url": f"{self.web}/phap-bao/{seo}/{book['categoryId']}/{book['id']}/{toc['value']}",
                        "title": f"{book['name']} - {toc['label']}",
                        "text": text,
                        "author": book.get("author") or "",
                        "date": book.get("publicationYearString") or "",
                        "category_raw": f"category: {book.get('seoCategoryName', '')} | {book.get('categoryName', '')} | {book['name']}",
                        "description": "",
                        "crawled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    })
                    done.add(doc_id)
                    n_new += 1
                log.info("[vbeta] xong sách: %s (tổng mới: %d)", book["name"], n_new)
        return n_new
