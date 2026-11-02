"""BM25 (Okapi) - truy hồi theo từ khóa. Bản TypeScript: web/lib/rag/retrieval/bm25.ts"""
from __future__ import annotations

import math
from collections import Counter, defaultdict

from ..nlp.normalize import bm25_tokenize


class BM25Index:
    def __init__(self, texts: list[str], k1: float = 1.2, b: float = 0.75):
        self.k1, self.b = k1, b
        self.doc_len: list[int] = []
        self.postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for i, text in enumerate(texts):
            tf = Counter(bm25_tokenize(text))
            self.doc_len.append(sum(tf.values()))
            for term, f in tf.items():
                self.postings[term].append((i, f))
        self.n = len(texts)
        self.avgdl = sum(self.doc_len) / max(1, self.n)

    def idf(self, term: str) -> float:
        df = len(self.postings.get(term, ()))
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def search(self, query: str, k: int = 30) -> list[tuple[int, float]]:
        scores: dict[int, float] = defaultdict(float)
        for term in set(bm25_tokenize(query)):
            idf = self.idf(term)
            for i, f in self.postings.get(term, ()):
                denom = f + self.k1 * (1 - self.b + self.b * self.doc_len[i] / self.avgdl)
                scores[i] += idf * f * (self.k1 + 1) / denom
        return sorted(scores.items(), key=lambda x: -x[1])[:k]
