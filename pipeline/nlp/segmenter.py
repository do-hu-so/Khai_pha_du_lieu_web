"""Tách từ tiếng Việt (word segmentation) cho các tác vụ khai phá văn bản.

- underthesea: tách từ ghép bằng CRF, "Phật giáo Việt Nam" -> ["Phật_giáo", "Việt_Nam"]
- syllable   : tách theo âm tiết (dự phòng khi chưa cài underthesea)
"""
from __future__ import annotations

import logging
import re

from .normalize import normalize_text
from .stopwords import is_stopword

log = logging.getLogger(__name__)

_WORD_RE = re.compile(r"^[\w_]+$", re.UNICODE)
_SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+|\n+")


class Segmenter:
    def __init__(self, method: str = "underthesea"):
        self.method = method
        self._word_tokenize = None
        if method == "underthesea":
            try:
                from underthesea import word_tokenize

                self._word_tokenize = word_tokenize
            except ImportError:
                log.warning("Chưa cài underthesea -> dùng tách theo âm tiết")
                self.method = "syllable"

    def tokenize(self, text: str) -> list[str]:
        """Trả về danh sách từ (chữ thường, từ ghép nối bằng '_')."""
        text = normalize_text(text)
        if self._word_tokenize is None:
            return [t for t in re.findall(r"\w+", text.lower()) if not t.isdigit()]
        tokens: list[str] = []
        for sent in _SENT_SPLIT.split(text):
            sent = sent.strip()
            if not sent:
                continue
            for w in self._word_tokenize(sent):
                w = w.lower().replace(" ", "_")
                if _WORD_RE.match(w) and not w.replace("_", "").isdigit():
                    tokens.append(w)
        return tokens

    def content_words(self, text: str, min_len: int = 2) -> list[str]:
        """Từ nội dung: đã bỏ stopword, số, từ quá ngắn."""
        return [w for w in self.tokenize(text) if len(w) >= min_len and not is_stopword(w)]
