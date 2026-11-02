"""Công cụ dòng lệnh thử truy hồi trên index đã build (không cần chạy web).

    python -m pipeline search "Tứ diệu đế là gì?"
    python -m pipeline search "thiền hành" --mode bm25 -k 5
"""
from __future__ import annotations

import textwrap

from ..config import INDEX_DIR
from ..embedding.build_index import load_index
from ..embedding.embedder import Embedder
from .bm25 import BM25Index
from .hybrid import HybridRetriever, dense_search


def run(query: str, mode: str = "hybrid", k: int = 5) -> None:
    manifest, chunks, vectors = load_index(INDEX_DIR)
    print(f"Index: {manifest['num_chunks']} chunk | mô hình {manifest['model_name']} | chế độ: {mode}\n")
    if mode == "bm25":
        hits = [{"index": i, "bm25_score": s} for i, s in BM25Index([f"{c['title']}\n{c['text']}" for c in chunks]).search(query, k)]
    else:
        embedder = Embedder(manifest["model_name"], manifest["passage_prefix"], manifest["query_prefix"])
        if mode == "dense":
            hits = [{"index": i, "dense_score": s} for i, s in dense_search(vectors, embedder.embed_query(query), k)]
        else:
            hits = HybridRetriever(chunks, vectors, embedder).search(query, top_k=k)

    for rank, h in enumerate(hits, 1):
        c = chunks[h["index"]]
        scores = " ".join(f"{key}={val:.4f}" if isinstance(val, float) else f"{key}={val}"
                          for key, val in h.items() if key not in ("index", "chunk"))
        print(f"#{rank} [{c['source']}] {c['title']}\n   {scores}\n   {c['url']}")
        print(textwrap.indent(textwrap.shorten(c["text"], 300), "   > ") + "\n")
