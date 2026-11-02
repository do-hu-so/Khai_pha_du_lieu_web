"""Gán nhãn chủ đề thống nhất cho văn bản theo luật trong config/categories.yaml."""
from __future__ import annotations

import re

from ..nlp.normalize import strip_accents


def _norm(s: str) -> str:
    # bỏ dấu, chữ thường, '_' và khoảng trắng -> '-' để URL và chữ thường so khớp như nhau
    return re.sub(r"[\s_]+", "-", strip_accents(s).lower())


class RuleCategorizer:
    def __init__(self, cfg: dict):
        self.default = cfg.get("default", "Khác")
        self.rules = []
        for r in cfg["rules"]:
            # so khớp trọn token: "tho" không khớp trong "thong-bach"
            pattern = "|".join(re.escape(_norm(k)) for k in r["keywords"])
            self.rules.append((r["label"], re.compile(rf"(?<![a-z0-9])(?:{pattern})(?![a-z0-9])")))

    def categorize(self, url: str, category_raw: str, title: str) -> str:
        # Ưu tiên chuyên mục gốc + URL; tiêu đề chỉ xét sau cùng (dễ nhiễu)
        for haystack in (f"{category_raw} {url}", title):
            h = _norm(haystack)
            for label, rx in self.rules:
                if rx.search(h):
                    return label
        return self.default
