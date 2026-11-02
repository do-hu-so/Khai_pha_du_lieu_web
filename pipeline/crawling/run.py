"""Bước 1 - THU THẬP: chạy crawler cho các nguồn trong config/sources.yaml (song song theo nguồn)."""
from __future__ import annotations

import logging
import shutil
from concurrent.futures import ThreadPoolExecutor

from ..config import MANUAL_DIR, RAW_DIR, ensure_dirs, sources_config
from .html_crawler import HtmlSiteCrawler
from .http import PoliteSession
from .manual_import import import_manual
from .vbeta_crawler import VbetaCrawler

log = logging.getLogger(__name__)


def _crawl_one(src: dict, fresh: bool) -> tuple[str, int]:
    out_dir = RAW_DIR / src["id"]
    if src["type"] == "manual":
        return src["id"], import_manual(MANUAL_DIR, RAW_DIR / "_manual_import", src["name"])
    if fresh and out_dir.exists():
        shutil.rmtree(out_dir)
    session = PoliteSession(
        user_agent=src["user_agent"],
        delay_seconds=float(src["delay_seconds"]),
        timeout_seconds=float(src["timeout_seconds"]),
        max_retries=int(src["max_retries"]),
        respect_robots=bool(src["respect_robots"]),
    )
    crawler_cls = {"html": HtmlSiteCrawler, "vbeta": VbetaCrawler}[src["type"]]
    try:
        return src["id"], crawler_cls(src, session, out_dir).run()
    except Exception:
        log.exception("[%s] crawler lỗi", src["id"])
        return src["id"], 0


def run(only: list[str] | None = None, fresh: bool = False, max_articles: int | None = None) -> None:
    ensure_dirs()
    cfg = sources_config()
    defaults = cfg.get("defaults", {})
    sources = []
    for s in cfg["sources"]:
        src = {**defaults, **s}
        if only and src["id"] not in only:
            continue
        if not src.get("enabled", True):
            log.info("[%s] bị tắt trong cấu hình -> bỏ qua", src["id"])
            continue
        if max_articles is not None:
            src["max_articles"] = max_articles
        sources.append(src)

    with ThreadPoolExecutor(max_workers=max(1, len(sources))) as ex:
        results = list(ex.map(lambda s: _crawl_one(s, fresh), sources))
    for sid, n in results:
        log.info("  %-16s +%d văn bản", sid, n)
