"""Bước 2 - TIỀN XỬ LÝ & SẮP XẾP: gộp dữ liệu thô các nguồn -> data/processed/corpus.jsonl

  làm sạch -> lọc (độ dài, ngôn ngữ) -> khử trùng lặp -> gán chủ đề thống nhất -> sắp xếp
"""
from __future__ import annotations

import logging
import re
from collections import Counter

from ..config import CORPUS_FILE, PROCESSED_DIR, RAW_DIR, categories_config, ensure_dirs, pipeline_config
from ..nlp.normalize import vietnamese_ratio
from ..utils.io import read_jsonl, write_json, write_jsonl
from .categorizer import RuleCategorizer
from .cleaner import TextCleaner
from .dedup import MinHashDeduper, fingerprint

log = logging.getLogger(__name__)


def run() -> None:
    ensure_dirs()
    cfg = pipeline_config()["preprocess"]
    cleaner = TextCleaner(cfg.get("boilerplate_patterns"), cfg.get("drop_foreign_lines", True))
    categorizer = RuleCategorizer(categories_config())
    deduper = MinHashDeduper()
    seen_fp, seen_url = set(), set()
    stats = Counter()
    docs = []

    for raw_file in sorted(RAW_DIR.glob("*/documents.jsonl")):
        for d in read_jsonl(raw_file):
            stats["raw"] += 1
            if d.get("url") and d["url"] in seen_url:
                stats["dup_url"] += 1
                continue
            text = cleaner.clean(d.get("text", ""))[: cfg["max_chars"]]
            if len(text) < cfg["min_chars"]:
                stats["too_short"] += 1
                continue
            if vietnamese_ratio(text) < cfg["min_vietnamese_ratio"]:
                stats["not_vietnamese"] += 1
                continue
            fp = fingerprint(text)
            if fp in seen_fp:
                stats["dup_exact"] += 1
                continue
            if deduper.is_duplicate(text):
                stats["dup_near"] += 1
                continue
            seen_fp.add(fp)
            seen_url.add(d.get("url"))
            title = cleaner.clean_title(d.get("title", "")) or text[:80]
            docs.append({
                "doc_id": d["id"],
                "source": d["source"],
                "source_name": d["source_name"],
                "url": d.get("url", ""),
                "title": title,
                "author": d.get("author", ""),
                "date": d.get("date", ""),
                "category_raw": d.get("category_raw", ""),
                "category": categorizer.categorize(d.get("url", ""), d.get("category_raw", ""), title),
                "n_chars": len(text),
                "n_syllables": len(re.findall(r"\w+", text)),
                "text": text,
            })

    # Sắp xếp kho: theo nguồn -> chủ đề -> tiêu đề
    docs.sort(key=lambda x: (x["source"], x["category"], x["title"]))
    write_jsonl(CORPUS_FILE, docs)
    stats["kept"] = len(docs)
    summary = {
        "filter_stats": dict(stats),
        "by_source": Counter(d["source"] for d in docs),
        "by_category": Counter(d["category"] for d in docs),
        "total_chars": sum(d["n_chars"] for d in docs),
    }
    write_json(PROCESSED_DIR / "corpus_summary.json", summary)
    log.info("Tiền xử lý: %s", dict(stats))
    log.info("Theo nguồn: %s", dict(summary["by_source"]))
    log.info("Theo chủ đề: %s", dict(summary["by_category"]))
    log.info("-> %s", CORPUS_FILE)
