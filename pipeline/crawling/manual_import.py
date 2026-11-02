"""Nhập tài liệu thủ công: đặt file vào data/raw/manual/<tên-nguồn>/...

Hỗ trợ: .txt .md .html .htm .pdf (cần pypdf) .docx (cần python-docx)
Có thể đặt file <tên>.meta.json cạnh tài liệu để khai báo: {"title", "url", "author", "category"}
Thư mục con cấp 1 được dùng làm tên nguồn (vd manual/thuvienhoasen/...).
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from ..utils.io import write_jsonl
from .extract import extract_article

log = logging.getLogger(__name__)

SUPPORTED = {".txt", ".md", ".html", ".htm", ".pdf", ".docx"}


def _read_file(path: Path) -> tuple[str, str]:
    """Trả về (title, text)."""
    ext = path.suffix.lower()
    if ext in (".txt", ".md"):
        return path.stem, path.read_text(encoding="utf-8", errors="ignore")
    if ext in (".html", ".htm"):
        doc = extract_article(path.read_text(encoding="utf-8", errors="ignore"), path.as_uri())
        return (doc["title"] or path.stem, doc["text"]) if doc else (path.stem, "")
    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return path.stem, "\n\n".join(p.extract_text() or "" for p in reader.pages)
    if ext == ".docx":
        import docx

        d = docx.Document(str(path))
        return path.stem, "\n\n".join(p.text for p in d.paragraphs)
    return path.stem, ""


def import_manual(manual_dir: Path, out_dir: Path, source_name: str) -> int:
    records = []
    for path in sorted(manual_dir.rglob("*")):
        if path.suffix.lower() not in SUPPORTED or path.name.lower() == "readme.md":
            continue
        try:
            title, text = _read_file(path)
        except Exception as e:  # file hỏng / thiếu thư viện đọc
            log.warning("Không đọc được %s: %s", path, e)
            continue
        if len(text.strip()) < 200:
            continue
        meta_file = path.with_suffix(".meta.json")
        meta = json.loads(meta_file.read_text(encoding="utf-8")) if meta_file.exists() else {}
        rel = path.relative_to(manual_dir)
        sub = rel.parts[0] if len(rel.parts) > 1 else "manual"
        records.append({
            "id": "manual-" + hashlib.sha1(str(rel).encode()).hexdigest()[:12],
            "source": "manual" if sub == "manual" else sub,
            "source_name": source_name if sub == "manual" else f"{sub} (nhập thủ công)",
            "url": meta.get("url", ""),
            "title": meta.get("title", title),
            "text": text.strip(),
            "author": meta.get("author", ""),
            "date": meta.get("date", ""),
            "category_raw": meta.get("category", str(rel.parent)),
            "description": "",
            "crawled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
    write_jsonl(out_dir / "documents.jsonl", records)
    log.info("[manual] nhập %d tài liệu từ %s", len(records), manual_dir)
    return len(records)
