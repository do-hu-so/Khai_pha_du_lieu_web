"""Bước 5 - EMBEDDING: data/chunks/chunks.jsonl -> data/index/ (+ copy sang web/data/index/)

Định dạng index (đọc được cả bằng Python lẫn Node.js, không cần vector DB):
  manifest.json   : thông tin mô hình, số chiều, số chunk, thống kê
  chunks.json     : mảng metadata + nội dung các chunk (thứ tự trùng với hàng của ma trận)
  embeddings.f32  : ma trận float32 little-endian [num_chunks x dim], đã chuẩn hóa L2
"""
from __future__ import annotations

import json
import logging
import shutil
import time
from collections import Counter
from datetime import datetime, timezone

import numpy as np

from ..config import CHUNKS_FILE, INDEX_DIR, WEB_INDEX_DIR, ensure_dirs, pipeline_config
from ..utils.io import read_jsonl, write_json
from .embedder import Embedder, passage_text

log = logging.getLogger(__name__)

INDEX_FILES = ("manifest.json", "chunks.json", "embeddings.f32")


def export_to_web() -> None:
    """Copy index sang web/data/index để ứng dụng Next.js (Vercel) đọc."""
    WEB_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    for name in INDEX_FILES:
        shutil.copy2(INDEX_DIR / name, WEB_INDEX_DIR / name)
    log.info("Đã copy index -> %s", WEB_INDEX_DIR)


def run(limit: int | None = None) -> None:
    ensure_dirs()
    cfg = pipeline_config()["embedding"]
    chunks = list(read_jsonl(CHUNKS_FILE))
    if limit:
        chunks = chunks[:limit]
    if not chunks:
        raise SystemExit("Chưa có chunk nào. Hãy chạy: python -m pipeline chunk")

    embedder = Embedder(cfg["model_name"], cfg["passage_prefix"], cfg["query_prefix"],
                        cfg["max_seq_length"], cfg["normalize"])
    t0 = time.time()
    vectors = embedder.embed_passages([passage_text(c) for c in chunks], cfg["batch_size"])
    log.info("Embedding %d chunk mất %.1f giây", len(chunks), time.time() - t0)

    vectors.astype("<f4").tofile(INDEX_DIR / "embeddings.f32")
    with open(INDEX_DIR / "chunks.json", "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, separators=(",", ":"))
    write_json(INDEX_DIR / "manifest.json", {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model_name": cfg["model_name"],
        "web_model_name": cfg["web_model_name"],
        "passage_prefix": cfg["passage_prefix"],
        "query_prefix": cfg["query_prefix"],
        "dim": int(vectors.shape[1]),
        "num_chunks": len(chunks),
        "num_docs": len({c["doc_id"] for c in chunks}),
        "normalized": bool(cfg["normalize"]),
        "dtype": "float32",
        "chunking": pipeline_config()["chunking"],
        "by_source": Counter(c["source"] for c in chunks),
        "by_category": Counter(c["category"] for c in chunks),
        "sources": {c["source"]: c["source_name"] for c in chunks},
    })
    size_mb = sum((INDEX_DIR / n).stat().st_size for n in INDEX_FILES) / 1e6
    log.info("Index: %d vector x %d chiều, %.1f MB -> %s", len(chunks), vectors.shape[1], size_mb, INDEX_DIR)
    export_to_web()


def load_index(index_dir=INDEX_DIR) -> tuple[dict, list[dict], np.ndarray]:
    manifest = json.loads((index_dir / "manifest.json").read_text(encoding="utf-8"))
    chunks = json.loads((index_dir / "chunks.json").read_text(encoding="utf-8"))
    vectors = np.fromfile(index_dir / "embeddings.f32", dtype="<f4").reshape(-1, manifest["dim"])
    return manifest, chunks, vectors
