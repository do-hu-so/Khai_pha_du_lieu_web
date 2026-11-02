"""Trích xuất nội dung chính (main content) từ HTML.

Dùng trafilatura (thuật toán loại bỏ boilerplate: menu, quảng cáo, footer ...).
Nếu trafilatura thất bại -> dùng BeautifulSoup lấy các thẻ <p> làm dự phòng.
"""
from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

try:
    import trafilatura
except ImportError:  # pragma: no cover
    trafilatura = None

_BREADCRUMB_SELECTORS = [
    "[itemtype*='BreadcrumbList']", ".breadcrumb", ".breadcrumbs", "#breadcrumb",
    ".bread-crumb", "nav[aria-label*='breadcrumb' i]", "[class*='breadcrumb']",
]


def html_to_text(html: str) -> str:
    """Chuyển đoạn HTML (vd nội dung từ API) thành văn bản, giữ ngắt đoạn."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    for br in soup.find_all("br"):
        br.replace_with("\n")
    blocks = []
    for el in soup.find_all(["p", "div", "h1", "h2", "h3", "h4", "li", "blockquote"]):
        if el.find(["p", "div", "h1", "h2", "h3", "h4", "li", "blockquote"]):
            continue  # chỉ lấy khối lá để tránh lặp nội dung
        t = el.get_text(" ", strip=False).strip()
        if t:
            blocks.append(t)
    text = "\n".join(blocks) if blocks else soup.get_text("\n")
    text = re.sub(r"[ \t\xa0]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def _breadcrumb(soup: BeautifulSoup) -> str:
    for sel in _BREADCRUMB_SELECTORS:
        el = soup.select_one(sel)
        if el:
            parts = [a.get_text(" ", strip=True) for a in el.find_all(["a", "span", "li"])]
            parts = [p for i, p in enumerate(parts) if p and p not in parts[:i]]
            if parts:
                return " > ".join(parts)[:300]
    return ""


def _meta(soup: BeautifulSoup, *names: str) -> str:
    for n in names:
        el = soup.find("meta", attrs={"property": n}) or soup.find("meta", attrs={"name": n})
        if el and el.get("content"):
            return el["content"].strip()
    return ""


def extract_article(html: str, url: str) -> dict | None:
    """Trả về {title, text, author, date, category_raw} hoặc None nếu không có nội dung."""
    soup = BeautifulSoup(html, "lxml")
    meta: dict = {}
    text = ""
    if trafilatura is not None:
        out = trafilatura.extract(
            html, url=url, output_format="json", with_metadata=True,
            include_comments=False, include_tables=True, favor_recall=True,
        )
        if out:
            meta = json.loads(out)
            text = meta.get("text") or ""

    if len(text) < 200:  # dự phòng
        paras = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        fallback = "\n\n".join(p for p in paras if len(p) > 40)
        if len(fallback) > len(text):
            text = fallback
    if not text.strip():
        return None

    title = (meta.get("title") or _meta(soup, "og:title") or
             (soup.title.get_text(strip=True) if soup.title else "")).strip()
    category_parts = [
        _breadcrumb(soup),
        _meta(soup, "article:section"),
        meta.get("categories") or "",
    ]
    return {
        "title": title,
        "text": text.strip(),
        "author": (meta.get("author") or _meta(soup, "author", "article:author") or "").strip(),
        "date": (meta.get("date") or _meta(soup, "article:published_time") or "").strip(),
        "category_raw": " | ".join(p for p in category_parts if p),
        "description": (meta.get("description") or _meta(soup, "description", "og:description") or "").strip(),
    }


def body_classes(html: str) -> set[str]:
    m = re.search(r"<body[^>]*class=[\"']([^\"']*)[\"']", html, re.IGNORECASE)
    return set(m.group(1).split()) if m else set()
