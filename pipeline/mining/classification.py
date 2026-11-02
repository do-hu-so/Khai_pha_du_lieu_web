"""Tác vụ 5 - PHÂN LOẠI VĂN BẢN có giám sát.

Hai bài toán:
  (a) chủ đề  : dự đoán nhãn chủ đề thống nhất (Kinh điển, Thiền và tu tập, ...)
  (b) nguồn   : dự đoán văn bản đến từ website nào (phong cách viết / biên tập)
Mô hình: TF-IDF (unigram + bigram từ) + Naive Bayes / Logistic Regression / Linear SVM.
Đánh giá: tập kiểm thử 20% (phân tầng) + kiểm định chéo 5-fold (macro-F1).
"""
from __future__ import annotations

from collections import Counter

import numpy as np
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import ConfusionMatrixDisplay, classification_report, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import make_pipeline
from sklearn.svm import LinearSVC

from .common import content_tokens, save_fig


def _bigrams(tokens: list[str]) -> list[str]:
    ct = content_tokens(tokens)
    return ct + [f"{a}|{b}" for a, b in zip(ct, ct[1:])]


def _models(random_state: int):
    def vec():
        return TfidfVectorizer(analyzer=lambda t: t, min_df=2, max_df=0.7, sublinear_tf=True, max_features=60000)

    return {
        "Naive Bayes": make_pipeline(vec(), ComplementNB()),
        "Logistic Regression": make_pipeline(vec(), LogisticRegression(max_iter=2000, C=5, class_weight="balanced")),
        "Linear SVM": make_pipeline(vec(), LinearSVC(C=0.5, class_weight="balanced", random_state=random_state)),
    }


def _task(docs: list[dict], label_key: str, random_state: int, min_class: int = 10) -> dict | None:
    counts = Counter(d[label_key] for d in docs)
    keep = [d for d in docs if counts[d[label_key]] >= min_class and d[label_key] != "Khác"]
    classes = sorted({d[label_key] for d in keep})
    if len(classes) < 2:
        return None
    X = [_bigrams(d["tokens"]) for d in keep]
    y = np.array([d[label_key] for d in keep])
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=random_state)

    cv = StratifiedKFold(5, shuffle=True, random_state=random_state)
    results, best_name, best_f1, best_model = {}, None, -1.0, None
    for name, model in _models(random_state).items():
        cv_f1 = cross_val_score(model, X_tr, y_tr, cv=cv, scoring="f1_macro")
        model.fit(X_tr, y_tr)
        test_f1 = f1_score(y_te, model.predict(X_te), average="macro")
        results[name] = {"cv_f1_macro": round(float(cv_f1.mean()), 4), "cv_std": round(float(cv_f1.std()), 4),
                         "test_f1_macro": round(float(test_f1), 4)}
        if test_f1 > best_f1:
            best_name, best_f1, best_model = name, test_f1, model

    y_pred = best_model.predict(X_te)
    fig, ax = plt.subplots(figsize=(1.2 * len(classes) + 3, 1.0 * len(classes) + 2))
    ConfusionMatrixDisplay.from_predictions(y_te, y_pred, ax=ax, cmap="YlOrBr", xticks_rotation=35, colorbar=False)
    ax.set_title(f"Ma trận nhầm lẫn ({label_key}) - {best_name}")
    fig_path = save_fig(fig, f"classification_{label_key}_confusion.png")

    # Đặc trưng có trọng số cao nhất mỗi lớp (diễn giải mô hình tuyến tính)
    top_features = {}
    clf, vec = best_model[-1], best_model[0]
    if hasattr(clf, "coef_") and clf.coef_.shape[0] == len(clf.classes_):
        vocab = np.array(vec.get_feature_names_out())
        for i, c in enumerate(clf.classes_):
            top_features[str(c)] = [vocab[j].replace("_", " ").replace("|", " + ") for j in np.argsort(-clf.coef_[i])[:10]]

    return {
        "label": label_key,
        "num_docs": len(keep),
        "class_counts": dict(Counter(y.tolist())),
        "models": results,
        "best_model": best_name,
        "report": classification_report(y_te, y_pred, output_dict=True, zero_division=0),
        "top_features": top_features,
        "figures": {"confusion": fig_path},
    }


def run(docs: list[dict], random_state: int = 42) -> dict:
    return {key: _task(docs, key, random_state) for key in ("category", "source")}
