"""Chia văn bản thành các đoạn (chunk) cho RAG.

Chiến lược "đệ quy theo cấu trúc": đoạn văn -> câu -> từ.
  1. Gom các đoạn văn liền kề cho tới khi đạt chunk_size ký tự.
  2. Đoạn văn dài hơn chunk_size được tách theo câu; câu quá dài tách theo từ.
  3. Chunk sau lặp lại phần cuối (~chunk_overlap ký tự, tính theo câu) của chunk trước
     để không mất ngữ cảnh ở ranh giới.
"""
from __future__ import annotations

import re

_SENT_RE = re.compile(r"(?<=[.!?…;:])\s+(?=[\"“'(\[]?[A-ZÀ-Ỹ0-9])|(?<=[.!?…])\s+")


def split_sentences(paragraph: str) -> list[str]:
    return [s.strip() for s in _SENT_RE.split(paragraph) if s.strip()]


def _split_long(unit: str, size: int) -> list[str]:
    words, parts, cur = unit.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > size:
            parts.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    return parts + ([cur] if cur else [])


class TextChunker:
    def __init__(self, chunk_size: int = 900, chunk_overlap: int = 150, min_chunk_chars: int = 120):
        assert chunk_overlap < chunk_size
        self.size, self.overlap, self.min_chars = chunk_size, chunk_overlap, min_chunk_chars

    def _units(self, text: str) -> list[tuple[str, bool]]:
        """Danh sách (đơn vị văn bản, có phải đầu đoạn văn hay không)."""
        units = []
        for para in re.split(r"\n\s*\n|\n", text):
            para = para.strip()
            if not para:
                continue
            if len(para) <= self.size:
                units.append((para, True))
                continue
            first = True
            for sent in split_sentences(para):
                for piece in (_split_long(sent, self.size) if len(sent) > self.size else [sent]):
                    units.append((piece, first))
                    first = False
        return units

    def split(self, text: str) -> list[str]:
        chunks: list[str] = []
        cur: list[tuple[str, bool]] = []
        cur_len = 0

        def join(units):  # đầu đoạn văn -> xuống dòng, cùng đoạn -> dấu cách
            out = ""
            for u, new_para in units:
                out += ("\n" if new_para else " ") + u if out else u
            return out

        for unit, new_para in self._units(text):
            if cur and cur_len + len(unit) + 1 > self.size:
                chunks.append(join(cur))
                # giữ lại các đơn vị cuối làm phần chồng lấp
                tail, tail_len = [], 0
                for u in reversed(cur):
                    if tail_len + len(u[0]) > self.overlap:
                        break
                    tail.insert(0, u)
                    tail_len += len(u[0]) + 1
                cur, cur_len = tail, tail_len
            cur.append((unit, new_para))
            cur_len += len(unit) + 1
        if cur:
            last = join(cur)
            if chunks and len(last) < self.min_chars:
                chunks[-1] = chunks[-1] + "\n" + last
            elif not chunks or last not in chunks[-1]:
                chunks.append(last)
        return chunks
