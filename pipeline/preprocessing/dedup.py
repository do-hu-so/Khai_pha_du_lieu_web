"""Khử trùng lặp: trùng chính xác (fingerprint) + gần trùng (MinHash trên shingle 5 âm tiết)."""
from __future__ import annotations

import hashlib
import re

import numpy as np

_WORD = re.compile(r"\w+", re.UNICODE)


def fingerprint(text: str) -> str:
    """Băm nội dung sau khi bỏ dấu câu/khoảng trắng/hoa thường."""
    return hashlib.md5(" ".join(_WORD.findall(text.lower())).encode("utf-8")).hexdigest()


class MinHashDeduper:
    """Phát hiện văn bản gần trùng (vd cùng 1 bài đăng lại ở 2 trang) bằng MinHash + LSH."""

    def __init__(self, num_perm: int = 64, bands: int = 16, threshold: float = 0.8, shingle: int = 5, seed: int = 1):
        rng = np.random.default_rng(seed)
        self.a = rng.integers(1, 2**31 - 1, num_perm, dtype=np.int64)
        self.b = rng.integers(0, 2**31 - 1, num_perm, dtype=np.int64)
        self.bands, self.rows = bands, num_perm // bands
        self.threshold, self.shingle = threshold, shingle
        self.buckets: dict[tuple, list[int]] = {}
        self.signatures: list[np.ndarray] = []

    def _signature(self, text: str) -> np.ndarray:
        words = _WORD.findall(text.lower()[:30000])
        shingles = {" ".join(words[i:i + self.shingle]) for i in range(max(1, len(words) - self.shingle + 1))}
        # hash 28 bit để phép nhân với a (31 bit) không tràn int64
        hashes = np.array([int(hashlib.md5(s.encode()).hexdigest()[:7], 16) for s in shingles], dtype=np.int64)
        return ((np.outer(hashes, self.a) + self.b) % (2**31 - 1)).min(axis=0)

    def is_duplicate(self, text: str) -> bool:
        """Trả về True nếu gần trùng với văn bản đã thêm; ngược lại thêm văn bản vào chỉ mục."""
        sig = self._signature(text)
        candidates = set()
        keys = [(i, tuple(sig[i * self.rows:(i + 1) * self.rows])) for i in range(self.bands)]
        for k in keys:
            candidates.update(self.buckets.get(k, []))
        for c in candidates:
            if np.mean(self.signatures[c] == sig) >= self.threshold:
                return True
        idx = len(self.signatures)
        self.signatures.append(sig)
        for k in keys:
            self.buckets.setdefault(k, []).append(idx)
        return False
