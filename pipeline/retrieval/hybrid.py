"""Truy hồi lai (hybrid): dense (cosine) + BM25, hợp nhất bằng Reciprocal Rank Fusion.

RRF(d) = sum_i  w_i / (k + rank_i(d))   - không cần chuẩn hóa thang điểm giữa 2 phương pháp.
Bản TypeScript: web/lib/rag/retrieval/hybrid.ts
"""
from __future__ import annotations

import numpy as np

from .bm25 import BM25Index


def dense_search(vectors: np.ndarray, query_vec: np.ndarray, k: int = 30) -> list[tuple[int, float]]:
    scores = vectors @ query_vec  # vector đã chuẩn hóa L2 -> tích vô hướng = cosine
    top = np.argpartition(-scores, min(k, len(scores) - 1))[:k]
    return sorted(((int(i), float(scores[i])) for i in top), key=lambda x: -x[1])


def rrf_fuse(rankings: dict[str, list[tuple[int, float]]], weights: dict[str, float] | None = None,
             k: int = 60) -> list[dict]:
    fused: dict[int, dict] = {}
    for name, ranking in rankings.items():
        w = (weights or {}).get(name, 1.0)
        for rank, (idx, score) in enumerate(ranking, start=1):
            item = fused.setdefault(idx, {"index": idx, "rrf": 0.0})
            item["rrf"] += w / (k + rank)
            item[f"{name}_rank"] = rank
            item[f"{name}_score"] = score
    return sorted(fused.values(), key=lambda x: -x["rrf"])


class HybridRetriever:
    def __init__(self, chunks: list[dict], vectors: np.ndarray, embedder):
        self.chunks, self.vectors, self.embedder = chunks, vectors, embedder
        self.bm25 = BM25Index([f"{c['title']}\n{c['text']}" for c in chunks])

    def search(self, query: str, top_k: int = 10, candidates: int = 30) -> list[dict]:
        dense = dense_search(self.vectors, self.embedder.embed_query(query), candidates)
        sparse = self.bm25.search(query, candidates)
        fused = rrf_fuse({"dense": dense, "bm25": sparse})[:top_k]
        return [{**f, "chunk": self.chunks[f["index"]]} for f in fused]
