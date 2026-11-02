"""Dữ liệu dùng chung cho các tác vụ khai phá: kho văn bản đã tách từ (có cache)."""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from tqdm import tqdm  # noqa: E402

from ..config import CORPUS_FILE, FIGURES_DIR, SEGMENTED_FILE, pipeline_config  # noqa: E402
from ..nlp.segmenter import Segmenter  # noqa: E402
from ..nlp.stopwords import is_stopword  # noqa: E402
from ..utils.io import read_jsonl, write_jsonl  # noqa: E402

log = logging.getLogger(__name__)

plt.rcParams.update({"figure.dpi": 110, "savefig.bbox": "tight", "font.size": 10})


def load_segmented(force: bool = False) -> list[dict]:
    """Mỗi phần tử: {doc_id, source, category, title, n_chars, tokens}. tokens: mọi từ (chữ thường).

    Cache (corpus_segmented.jsonl) chỉ lưu {doc_id, hash, tokens}: metadata (chủ đề, tiêu đề) luôn
    lấy mới từ corpus.jsonl, chỉ văn bản có nội dung thay đổi mới phải tách từ lại.
    """
    cfg = pipeline_config()["mining"]
    max_chars = cfg["max_chars_per_doc"]
    cache = {} if force else {r["doc_id"]: r for r in read_jsonl(SEGMENTED_FILE) if "hash" in r}
    seg = None
    docs, fresh = [], []
    for d in tqdm(list(read_jsonl(CORPUS_FILE)), desc="Tách từ"):
        text = d["text"][:max_chars]
        h = hashlib.md5(f"{cfg['segmenter']}|{text}".encode("utf-8")).hexdigest()[:16]
        cached = cache.get(d["doc_id"])
        if cached and cached["hash"] == h:
            tokens = cached["tokens"]
        else:
            if seg is None:
                seg = Segmenter(cfg["segmenter"])
                log.info("Tách từ bằng '%s' (cache tại %s)", seg.method, SEGMENTED_FILE)
            tokens = seg.tokenize(text)
            fresh.append(d["doc_id"])
        docs.append({"doc_id": d["doc_id"], "source": d["source"], "category": d["category"],
                     "title": d["title"], "n_chars": d["n_chars"], "hash": h, "tokens": tokens})
    if fresh or len(cache) != len(docs):
        write_jsonl(SEGMENTED_FILE, ({"doc_id": x["doc_id"], "hash": x["hash"], "tokens": x["tokens"]} for x in docs))
    log.info("Tách từ: %d văn bản (%d mới, %d lấy từ cache)", len(docs), len(fresh), len(docs) - len(fresh))
    return docs


def content_tokens(tokens: list[str]) -> list[str]:
    return [t for t in tokens if len(t) >= 2 and not is_stopword(t)]


def save_fig(fig, name: str) -> str:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURES_DIR / name
    fig.savefig(path)
    plt.close(fig)
    return f"figures/{name}"


def vietnamese_font() -> str | None:
    """Font có đủ glyph tiếng Việt cho WordCloud."""
    for p in ("C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/Library/Fonts/Arial Unicode.ttf"):
        if Path(p).exists():
            return p
    return None
