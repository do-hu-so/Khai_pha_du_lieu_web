"""Tác vụ 2 - TRÍCH XUẤT TỪ KHÓA bằng TF-IDF (theo văn bản và theo chủ đề) + đám mây từ."""
from __future__ import annotations

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from ..config import PROCESSED_DIR
from ..utils.io import write_jsonl
from .common import content_tokens, save_fig, vietnamese_font


def build_tfidf(docs: list[dict], **kwargs):
    vec = TfidfVectorizer(analyzer=lambda toks: toks, min_df=kwargs.get("min_df", 2),
                          max_df=kwargs.get("max_df", 0.6), sublinear_tf=True)
    X = vec.fit_transform([content_tokens(d["tokens"]) for d in docs])
    return vec, X


def run(docs: list[dict], top_k: int = 20) -> dict:
    vec, X = build_tfidf(docs)
    vocab = np.array(vec.get_feature_names_out())

    # Từ khóa của từng văn bản -> data/processed/doc_keywords.jsonl
    rows = []
    for i, d in enumerate(docs):
        row = X.getrow(i)
        idx = row.indices[np.argsort(-row.data)][:10]
        rows.append({"doc_id": d["doc_id"], "title": d["title"], "keywords": [vocab[j].replace("_", " ") for j in idx]})
    write_jsonl(PROCESSED_DIR / "doc_keywords.jsonl", rows)

    # Từ khóa đặc trưng của từng chủ đề (trung bình TF-IDF các văn bản thuộc chủ đề)
    cats = sorted({d["category"] for d in docs})
    labels = np.array([d["category"] for d in docs])
    by_category, figs = {}, {}
    try:
        from wordcloud import WordCloud
    except ImportError:
        WordCloud = None
    for cat in cats:
        mean = np.asarray(X[labels == cat].mean(axis=0)).ravel()
        top = np.argsort(-mean)[:top_k]
        by_category[cat] = [(vocab[j].replace("_", " "), round(float(mean[j]), 4)) for j in top]
        if WordCloud is not None:
            freqs = {vocab[j].replace("_", " "): float(mean[j]) for j in np.argsort(-mean)[:120] if mean[j] > 0}
            if freqs:
                wc = WordCloud(width=900, height=450, background_color="white", font_path=vietnamese_font(),
                               colormap="copper").generate_from_frequencies(freqs)
                import matplotlib.pyplot as plt

                fig, ax = plt.subplots(figsize=(9, 4.5))
                ax.imshow(wc), ax.axis("off"), ax.set_title(f"Đám mây từ khóa: {cat}")
                safe = "".join(ch if ch.isalnum() else "_" for ch in cat)
                figs[cat] = save_fig(fig, f"wordcloud_{safe}.png")

    examples = [r for r in rows[:: max(1, len(rows) // 8)]][:8]
    return {"by_category": by_category, "doc_examples": examples, "figures": figs, "vocab_size": len(vocab)}
