"""Đường dẫn và cấu hình dùng chung cho toàn bộ pipeline."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"

# ---- Thư mục dữ liệu (mọi dữ liệu nằm trong data/) ----
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"                  # dữ liệu thô sau khi crawl, mỗi nguồn 1 thư mục
MANUAL_DIR = RAW_DIR / "manual"             # file người dùng tự thêm
PROCESSED_DIR = DATA_DIR / "processed"      # kho văn bản đã làm sạch
CORPUS_FILE = PROCESSED_DIR / "corpus.jsonl"
SEGMENTED_FILE = PROCESSED_DIR / "corpus_segmented.jsonl"
CHUNKS_DIR = DATA_DIR / "chunks"
CHUNKS_FILE = CHUNKS_DIR / "chunks.jsonl"
INDEX_DIR = DATA_DIR / "index"              # vector index (embedding) - bản gốc

# ---- Kết quả khai phá ----
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

# ---- Ứng dụng web đọc index tại đây (được copy từ data/index khi build) ----
WEB_INDEX_DIR = ROOT / "web" / "data" / "index"


def _load_yaml(name: str) -> dict:
    with open(CONFIG_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache
def sources_config() -> dict:
    return _load_yaml("sources.yaml")


@lru_cache
def pipeline_config() -> dict:
    return _load_yaml("pipeline.yaml")


@lru_cache
def categories_config() -> dict:
    return _load_yaml("categories.yaml")


def ensure_dirs() -> None:
    for d in (RAW_DIR, MANUAL_DIR, PROCESSED_DIR, CHUNKS_DIR, INDEX_DIR, FIGURES_DIR, WEB_INDEX_DIR):
        d.mkdir(parents=True, exist_ok=True)
