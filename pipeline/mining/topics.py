"""Tác vụ 3 - MÔ HÌNH CHỦ ĐỀ (Topic Modeling) bằng LDA (Latent Dirichlet Allocation)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer

from .common import content_tokens, save_fig


def run(docs: list[dict], n_topics: int = 10, random_state: int = 42, top_n: int = 12) -> dict:
    vec = CountVectorizer(analyzer=lambda toks: toks, min_df=3, max_df=0.5)
    X = vec.fit_transform([content_tokens(d["tokens"]) for d in docs])
    lda = LatentDirichletAllocation(n_components=n_topics, learning_method="batch", max_iter=30,
                                    random_state=random_state)
    doc_topic = lda.fit_transform(X)
    vocab = np.array(vec.get_feature_names_out())

    topics = []
    for k, comp in enumerate(lda.components_):
        top = np.argsort(-comp)[:top_n]
        topics.append({
            "topic": k,
            "words": [vocab[i].replace("_", " ") for i in top],
            "share": round(float(doc_topic[:, k].mean()), 4),
        })

    # Ma trận chủ đề LDA x nhãn chủ đề (để diễn giải các topic)
    dominant = doc_topic.argmax(axis=1)
    ct = pd.crosstab(pd.Series([d["category"] for d in docs], name="Nhãn chủ đề"),
                     pd.Series([f"T{k}" for k in dominant], name="Topic LDA"))
    fig, ax = plt.subplots(figsize=(1 + 0.7 * n_topics, 0.6 * len(ct) + 1.5))
    im = ax.imshow(ct.values, cmap="YlOrBr")
    ax.set_xticks(range(ct.shape[1]), ct.columns), ax.set_yticks(range(ct.shape[0]), ct.index)
    for i in range(ct.shape[0]):
        for j in range(ct.shape[1]):
            ax.text(j, i, ct.values[i, j], ha="center", va="center", fontsize=8)
    ax.set_title("Phân bố topic LDA trội theo nhãn chủ đề")
    fig.colorbar(im, ax=ax, shrink=0.7)
    fig_path = save_fig(fig, "lda_topics_vs_category.png")

    examples = {}
    for k in range(n_topics):
        best = np.argsort(-doc_topic[:, k])[:3]
        examples[k] = [docs[i]["title"] for i in best]

    return {
        "n_topics": n_topics,
        "perplexity": round(float(lda.perplexity(X)), 2),
        "topics": topics,
        "examples": examples,
        "figures": {"heatmap": fig_path},
    }
