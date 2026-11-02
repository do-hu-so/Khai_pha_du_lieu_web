"""Tác vụ 6 - NHẬN DẠNG THỰC THỂ ĐỊNH DANH (NER): tên người (PER), địa danh (LOC), tổ chức (ORG).

Dùng underthesea.ner (CRF, nhãn BIO). Chạy trên mẫu ngẫu nhiên vì NER khá chậm.
"""
from __future__ import annotations

import logging
import random
import re
from collections import Counter

import matplotlib.pyplot as plt

from ..config import CORPUS_FILE
from ..utils.io import read_jsonl
from .common import save_fig

log = logging.getLogger(__name__)


def _entities(tagged) -> list[tuple[str, str]]:
    ents, cur, cur_type = [], [], None
    for item in tagged:
        word, tag = item[0], item[-1]
        if tag.startswith("B-"):
            if cur:
                ents.append((" ".join(cur), cur_type))
            cur, cur_type = [word], tag[2:]
        elif tag.startswith("I-") and cur and tag[2:] == cur_type:
            cur.append(word)
        else:
            if cur:
                ents.append((" ".join(cur), cur_type))
            cur, cur_type = [], None
    if cur:
        ents.append((" ".join(cur), cur_type))
    return ents


def run(sample_docs: int = 150, random_state: int = 42, max_sentences: int = 60) -> dict | None:
    try:
        from underthesea import ner
    except ImportError:
        log.warning("Chưa cài underthesea -> bỏ qua NER")
        return None
    docs = list(read_jsonl(CORPUS_FILE))
    random.Random(random_state).shuffle(docs)
    counts = {"PER": Counter(), "LOC": Counter(), "ORG": Counter()}
    for d in docs[:sample_docs]:
        sents = [s for s in re.split(r"(?<=[.!?])\s+|\n+", d["text"]) if 20 < len(s) < 400][:max_sentences]
        for s in sents:
            try:
                for ent, typ in _entities(ner(s)):
                    if typ in counts and len(ent) > 1:
                        counts[typ][ent.replace("_", " ")] += 1
            except Exception:  # câu lỗi định dạng -> bỏ qua
                continue

    fig, axes = plt.subplots(1, 3, figsize=(16, 6))
    colors = {"PER": "#b5651d", "LOC": "#6b8e23", "ORG": "#4682b4"}
    for ax, (typ, c) in zip(axes, counts.items()):
        top = c.most_common(15)[::-1]
        ax.barh([e for e, _ in top], [n for _, n in top], color=colors[typ])
        ax.set_title({"PER": "Nhân vật (PER)", "LOC": "Địa danh (LOC)", "ORG": "Tổ chức (ORG)"}[typ])
    fig_path = save_fig(fig, "ner_top_entities.png")
    return {
        "sample_docs": min(sample_docs, len(docs)),
        "top": {t: c.most_common(25) for t, c in counts.items()},
        "figures": {"top_entities": fig_path},
    }
