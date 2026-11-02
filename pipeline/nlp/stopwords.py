"""Danh sách từ dừng (stopwords) tiếng Việt - chỉnh sửa trong resources/vietnamese_stopwords.txt."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_FILE = Path(__file__).parent / "resources" / "vietnamese_stopwords.txt"


@lru_cache
def stopwords() -> frozenset[str]:
    words = set()
    for line in _FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip().lower()
        if line and not line.startswith("#"):
            words.add(line.replace(" ", "_"))
    return frozenset(words)


def is_stopword(word: str) -> bool:
    return word.lower() in stopwords()
