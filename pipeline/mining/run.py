"""Bước 3 - KHAI PHÁ VĂN BẢN & XLNNTN trên kho đã xây dựng -> reports/"""
from __future__ import annotations

import logging
import time

from ..config import REPORTS_DIR, ensure_dirs, pipeline_config
from ..utils.io import write_json
from . import classification, clustering, keywords, ner, statistics, topics
from .common import load_segmented
from .report import write_report

log = logging.getLogger(__name__)

ALL_TASKS = ["stats", "keywords", "topics", "clustering", "classification", "ner"]


def run(tasks: list[str] | None = None, resegment: bool = False) -> None:
    ensure_dirs()
    cfg = pipeline_config()["mining"]
    tasks = tasks or ALL_TASKS
    docs = load_segmented(force=resegment)
    log.info("Khai phá trên %d văn bản, tác vụ: %s", len(docs), tasks)
    rs = cfg["random_state"]
    jobs = {
        "stats": ("statistics", lambda: statistics.run(docs)),
        "keywords": ("keywords", lambda: keywords.run(docs, cfg["top_keywords"])),
        "topics": ("topics", lambda: topics.run(docs, cfg["lda_topics"], rs)),
        "clustering": ("clustering", lambda: clustering.run(docs, cfg["kmeans_k"], rs)),
        "classification": ("classification", lambda: classification.run(docs, rs)),
        "ner": ("ner", lambda: ner.run(cfg["ner_sample_docs"], rs)),
    }
    results = {}
    for t in tasks:
        name, fn = jobs[t]
        t0 = time.time()
        results[name] = fn()
        write_json(REPORTS_DIR / f"{name}.json", results[name])
        log.info("  ✓ %-15s (%.1fs)", name, time.time() - t0)
    log.info("Báo cáo: %s", write_report(results))
