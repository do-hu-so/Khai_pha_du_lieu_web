"""Chuẩn hóa văn bản tiếng Việt.

Các hàm ở đây được dùng ở CẢ pipeline Python lẫn web (web/lib/rag/text/normalize.ts
là bản port 1-1). Nếu sửa logic ở đây, hãy sửa cả file TypeScript để BM25 khớp nhau.
"""
from __future__ import annotations

import re
import unicodedata

VI_CHARS = "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
_VI_CHAR_SET = set(VI_CHARS)
_LETTERS = "a-z" + VI_CHARS
_TOKEN_RE = re.compile(r"[0-9" + _LETTERS + r"]+")

# Hai kiểu bỏ dấu cùng tồn tại: "hoà/hòa", "thuỷ/thủy", "khoẻ/khỏe".
# Ta thống nhất về kiểu phổ biến (dấu trên nguyên âm đầu): hòa, thủy, khỏe.
# Chỉ áp dụng khi cụm nguyên âm nằm CUỐI âm tiết ("toàn" giữ nguyên) và không sau "q" ("quý").
_VARIANT_TO_CANONICAL = {
    "oà": "òa", "oá": "óa", "oả": "ỏa", "oã": "õa", "oạ": "ọa",
    "oè": "òe", "oé": "óe", "oẻ": "ỏe", "oẽ": "õe", "oẹ": "ọe",
    "uỳ": "ùy", "uý": "úy", "uỷ": "ủy", "uỹ": "ũy", "uỵ": "ụy",
}
_TONE_RE = re.compile(
    r"(?<!q)(" + "|".join(_VARIANT_TO_CANONICAL) + r")(?![" + _LETTERS + r"])",
    re.IGNORECASE,
)


def normalize_unicode(text: str) -> str:
    """Đưa về dạng NFC (dựng sẵn) - nhiều trang dùng dạng tổ hợp (NFD) gây lệch khi so khớp."""
    return unicodedata.normalize("NFC", text)


def normalize_tone(text: str) -> str:
    def repl(m: re.Match) -> str:
        s = m.group(0)
        out = _VARIANT_TO_CANONICAL.get(s.lower(), s)
        return out.upper() if s.isupper() else (out[0].upper() + out[1:] if s[0].isupper() else out)

    return _TONE_RE.sub(repl, text)


def normalize_text(text: str) -> str:
    return normalize_tone(normalize_unicode(text))


def strip_accents(text: str) -> str:
    """Bỏ dấu tiếng Việt: 'Phật giáo' -> 'Phat giao'."""
    text = text.replace("đ", "d").replace("Đ", "D")
    nfd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def vietnamese_ratio(text: str) -> float:
    """Tỉ lệ token chứa ký tự đặc trưng tiếng Việt - dùng để lọc bài tiếng nước ngoài."""
    tokens = _TOKEN_RE.findall(text.lower()[:20000])
    if not tokens:
        return 0.0
    vi = sum(1 for t in tokens if any(c in _VI_CHAR_SET for c in t))
    return vi / len(tokens)


# Chữ Pāli/Sanskrit (Samaṇa, Saṅgha, Nibbāna) -> chữ Latin cơ bản để khớp cả cách viết không dấu
_PALI = str.maketrans("āīūṅñṭḍṇḷṃṁḥśṣṛṝḹ", "aiunntdnlmmhssrrl")


def syllables(text: str) -> list[str]:
    return _TOKEN_RE.findall(normalize_text(text).lower().translate(_PALI))


def bm25_tokenize(text: str) -> list[str]:
    """Token hóa cho BM25: âm tiết + cặp âm tiết liền kề (bigram).

    Tiếng Việt là ngôn ngữ đơn lập, từ ghép gồm nhiều âm tiết ("vô thường", "niết bàn").
    Thêm bigram giúp BM25 bắt được từ ghép mà không cần bộ tách từ ở phía web.
    """
    syl = syllables(text)
    return syl + [f"{a}_{b}" for a, b in zip(syl, syl[1:])]
