"""Làm sạch văn bản: chuẩn hóa Unicode/dấu thanh, xóa ký tự rác, dòng boilerplate, khoảng trắng."""
from __future__ import annotations

import re

from ..nlp.normalize import normalize_text, vietnamese_ratio

_CONTROL = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f​-‏﻿]")
_SPACES = re.compile(r"[ \t\xa0 - 　]+")
_MANY_NEWLINES = re.compile(r"\n{3,}")
_ONLY_SYMBOLS = re.compile(r"^[\W_]+$")
_URL = re.compile(r"https?://\S+")


class TextCleaner:
    def __init__(self, boilerplate_patterns: list[str] | None = None, drop_foreign_lines: bool = True):
        self.boilerplate = [re.compile(p, re.IGNORECASE) for p in (boilerplate_patterns or [])]
        self.drop_foreign_lines = drop_foreign_lines

    @staticmethod
    def _is_foreign(line: str) -> bool:
        """Dòng dài (>= 8 từ) gần như không có chữ có dấu tiếng Việt -> đoạn tiếng nước ngoài
        (vd bản tiếng Anh trong bài song ngữ). Dòng ngắn (tên riêng, kệ Pāli) được giữ lại."""
        return len(line.split()) >= 8 and vietnamese_ratio(line) < 0.05

    def clean(self, text: str) -> str:
        text = normalize_text(text)
        text = _CONTROL.sub("", text).replace("\r\n", "\n").replace("\r", "\n")
        text = _URL.sub("", text)
        lines = []
        for line in text.split("\n"):
            line = _SPACES.sub(" ", line).strip()
            if line and (_ONLY_SYMBOLS.match(line) or any(p.search(line) for p in self.boilerplate)
                         or (self.drop_foreign_lines and self._is_foreign(line))):
                continue
            lines.append(line)
        text = "\n".join(lines)
        return _MANY_NEWLINES.sub("\n\n", text).strip()

    @staticmethod
    def clean_title(title: str) -> str:
        # Hậu tố tên site (vd "... - Tủ Sách Phật Giáo") được xử lý riêng từng nguồn bằng
        # title_strip_regex trong sources.yaml, vì dấu " - " còn dùng trong tên chương sách.
        return normalize_text(_SPACES.sub(" ", title or "")).strip()
