"""Tác vụ 4 - PHÂN CỤM VĂN BẢN: TF-IDF -> LSA (TruncatedSVD) -> K-Means, trực quan hóa 2D."""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.manifold import TSNE
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score, silhouette_score
from sklearn.preprocessing import Normalizer

from .common import save_fig
from .keywords import build_tfidf


def run(docs: list[dict], k: int = 8, random_state: int = 42) -> dict:
    vec, X = build_tfidf(docs)
    n_comp = min(100, X.shape[1] - 1, X.shape[0] - 1)
    Z = Normalizer().fit_transform(TruncatedSVD(n_comp, random_state=random_state).fit_transform(X))

    # Khảo sát số cụm bằng silhouette
    k_range = [kk for kk in range(2, 15) if kk < len(docs)]
    sil = {}
    for kk in k_range:
        labels_k = KMeans(kk, n_init=5, random_state=random_state).fit_predict(Z)
        sil[kk] = round(float(silhouette_score(Z, labels_k, sample_size=min(3000, len(docs)), random_state=random_state)), 4)

    km = KMeans(k, n_init=10, random_state=random_state).fit(Z)
    labels = km.labels_
    vocab = np.array(vec.get_feature_names_out())
    clusters = []
    for c in range(k):
        members = np.where(labels == c)[0]
        mean = np.asarray(X[members].mean(axis=0)).ravel()
        cats = np.unique([docs[i]["category"] for i in members], return_counts=True)
        clusters.append({
            "cluster": c, "size": int(len(members)),
            "top_terms": [vocab[i].replace("_", " ") for i in np.argsort(-mean)[:10]],
            "main_category": str(cats[0][np.argmax(cats[1])]) if len(members) else "",
            "examples": [docs[i]["title"] for i in members[:3]],
        })

    true = [d["category"] for d in docs]
    xy = TSNE(2, random_state=random_state, init="pca", perplexity=min(30, max(5, len(docs) // 10))).fit_transform(Z)
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    axes[0].scatter(xy[:, 0], xy[:, 1], c=labels, cmap="tab10", s=8)
    axes[0].set_title(f"t-SNE - tô màu theo cụm K-Means (k={k})")
    for cat in sorted(set(true)):
        m = np.array(true) == cat
        axes[1].scatter(xy[m, 0], xy[m, 1], s=8, label=cat)
    axes[1].legend(fontsize=8, markerscale=2), axes[1].set_title("t-SNE - tô màu theo nhãn chủ đề")
    fig_tsne = save_fig(fig, "clustering_tsne.png")

    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.plot(list(sil), list(sil.values()), "o-", color="#8b4513")
    ax.set_xlabel("Số cụm k"), ax.set_ylabel("Silhouette"), ax.set_title("Chọn số cụm bằng hệ số Silhouette")
    fig_sil = save_fig(fig, "clustering_silhouette.png")

    return {
        "k": k,
        "silhouette_by_k": sil,
        "silhouette": round(float(silhouette_score(Z, labels, sample_size=min(3000, len(docs)), random_state=random_state)), 4),
        "ari_vs_category": round(float(adjusted_rand_score(true, labels)), 4),
        "nmi_vs_category": round(float(normalized_mutual_info_score(true, labels)), 4),
        "clusters": clusters,
        "figures": {"tsne": fig_tsne, "silhouette": fig_sil},
    }
