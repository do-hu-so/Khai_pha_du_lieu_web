"""Tác vụ 1 - THỐNG KÊ KHO VĂN BẢN: quy mô, phân bố độ dài, từ vựng, định luật Zipf, n-gram."""
from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .common import content_tokens, save_fig


def run(docs: list[dict]) -> dict:
    df = pd.DataFrame([{"source": d["source"], "category": d["category"], "n_chars": d["n_chars"],
                        "n_words": len(d["tokens"])} for d in docs])
    by_source = df.groupby("source").agg(docs=("n_chars", "size"), chars=("n_chars", "sum"),
                                         mean_words=("n_words", "mean")).round(1)
    by_category = df.groupby("category").agg(docs=("n_chars", "size"), chars=("n_chars", "sum")).sort_values("docs", ascending=False)

    word_freq = Counter(t for d in docs for t in d["tokens"])
    content_freq = Counter(t for d in docs for t in content_tokens(d["tokens"]))
    compound = {w: c for w, c in content_freq.items() if "_" in w}
    bigram_freq = Counter()
    for d in docs:
        ct = content_tokens(d["tokens"])
        bigram_freq.update(f"{a} {b}" for a, b in zip(ct, ct[1:]))
    n_tokens = sum(word_freq.values())

    figs = {}
    # Phân bố số văn bản theo nguồn / chủ đề
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    by_source["docs"].sort_values().plot.barh(ax=axes[0], color="#b5651d", title="Số văn bản theo nguồn")
    by_category["docs"].sort_values().plot.barh(ax=axes[1], color="#6b8e23", title="Số văn bản theo chủ đề")
    figs["distribution"] = save_fig(fig, "stats_distribution.png")

    # Độ dài văn bản theo nguồn
    fig, ax = plt.subplots(figsize=(8, 4))
    df.boxplot(column="n_words", by="source", ax=ax, showfliers=False)
    ax.set_title("Độ dài văn bản (số từ) theo nguồn"), ax.set_xlabel(""), fig.suptitle("")
    figs["length"] = save_fig(fig, "stats_length_by_source.png")

    # Top từ nội dung
    top = content_freq.most_common(30)
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.barh([w.replace("_", " ") for w, _ in reversed(top)], [c for _, c in reversed(top)], color="#cd853f")
    ax.set_title("30 từ (đã bỏ từ dừng) xuất hiện nhiều nhất")
    figs["top_words"] = save_fig(fig, "stats_top_words.png")

    # Định luật Zipf: tần suất ~ 1 / hạng
    freqs = np.array(sorted(word_freq.values(), reverse=True))
    ranks = np.arange(1, len(freqs) + 1)
    slope = float(np.polyfit(np.log(ranks[:5000]), np.log(freqs[:5000]), 1)[0]) if len(freqs) > 10 else 0.0
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.loglog(ranks, freqs, ".", markersize=2, color="#8b4513")
    ax.set_xlabel("Hạng (log)"), ax.set_ylabel("Tần suất (log)")
    ax.set_title(f"Định luật Zipf - độ dốc ≈ {slope:.2f}")
    figs["zipf"] = save_fig(fig, "stats_zipf.png")

    return {
        "num_docs": len(docs),
        "num_tokens": n_tokens,
        "vocab_size": len(word_freq),
        "type_token_ratio": round(len(word_freq) / max(1, n_tokens), 4),
        "compound_word_ratio": round(sum(1 for w in word_freq if "_" in w) / max(1, len(word_freq)), 4),
        "zipf_slope": round(slope, 3),
        "by_source": by_source.reset_index().to_dict("records"),
        "by_category": by_category.reset_index().to_dict("records"),
        "top_words": content_freq.most_common(50),
        "top_compound_words": Counter(compound).most_common(30),
        "top_bigrams": bigram_freq.most_common(30),
        "figures": figs,
    }
