"""Tổng hợp kết quả khai phá thành reports/REPORT.md (kèm hình trong reports/figures/)."""
from __future__ import annotations

from datetime import datetime

from ..config import REPORTS_DIR


def _table(headers: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def write_report(results: dict) -> str:
    L = [f"# Báo cáo khai phá kho văn bản Phật giáo tiếng Việt",
         f"_Sinh tự động lúc {datetime.now():%Y-%m-%d %H:%M} bởi `python -m pipeline mine`_\n"]

    s = results.get("statistics")
    if s:
        L += ["## 1. Thống kê kho văn bản",
              _table(["Chỉ số", "Giá trị"], [
                  ["Số văn bản", s["num_docs"]], ["Số từ (token)", f"{s['num_tokens']:,}"],
                  ["Kích thước từ vựng", f"{s['vocab_size']:,}"], ["Type/Token ratio", s["type_token_ratio"]],
                  ["Tỉ lệ từ ghép trong từ vựng", s["compound_word_ratio"]], ["Độ dốc Zipf", s["zipf_slope"]]]),
              "", "### Theo nguồn",
              _table(["Nguồn", "Văn bản", "Ký tự", "Số từ TB"],
                     [[r["source"], r["docs"], f"{r['chars']:,}", r["mean_words"]] for r in s["by_source"]]),
              "", "### Theo chủ đề",
              _table(["Chủ đề", "Văn bản", "Ký tự"], [[r["category"], r["docs"], f"{r['chars']:,}"] for r in s["by_category"]]),
              "", *[f"![{k}]({v})" for k, v in s["figures"].items()], "",
              "**Từ ghép phổ biến:** " + ", ".join(w.replace("_", " ") for w, _ in s["top_compound_words"][:25]), "",
              "**Cụm 2 từ phổ biến:** " + ", ".join(b.replace("_", " ") for b, _ in s["top_bigrams"][:20]), ""]

    k = results.get("keywords")
    if k:
        L += ["## 2. Trích xuất từ khóa (TF-IDF)",
              _table(["Chủ đề", "Từ khóa đặc trưng"], [[c, ", ".join(w for w, _ in ws[:12])] for c, ws in k["by_category"].items()]),
              "", "### Ví dụ từ khóa của từng văn bản",
              _table(["Văn bản", "Từ khóa"], [[e["title"][:70], ", ".join(e["keywords"][:8])] for e in k["doc_examples"]]),
              "", *[f"![{c}]({p})" for c, p in k["figures"].items()], ""]

    t = results.get("topics")
    if t:
        L += [f"## 3. Mô hình chủ đề LDA ({t['n_topics']} topic, perplexity = {t['perplexity']})",
              _table(["Topic", "Tỉ trọng", "Từ tiêu biểu", "Văn bản tiêu biểu"],
                     [[f"T{x['topic']}", x["share"], ", ".join(x["words"][:10]), "; ".join(a[:40] for a in t["examples"][x["topic"]][:2])]
                      for x in t["topics"]]),
              "", f"![lda]({t['figures']['heatmap']})", ""]

    c = results.get("clustering")
    if c:
        L += [f"## 4. Phân cụm văn bản (K-Means trên LSA, k={c['k']})",
              f"Silhouette = **{c['silhouette']}**, ARI so với nhãn chủ đề = **{c['ari_vs_category']}**, "
              f"NMI = **{c['nmi_vs_category']}**\n",
              _table(["Cụm", "Số VB", "Chủ đề chính", "Từ đặc trưng"],
                     [[x["cluster"], x["size"], x["main_category"], ", ".join(x["top_terms"][:8])] for x in c["clusters"]]),
              "", f"![tsne]({c['figures']['tsne']})", f"![sil]({c['figures']['silhouette']})", ""]

    cl = results.get("classification")
    if cl:
        L += ["## 5. Phân loại văn bản"]
        for key, r in cl.items():
            if not r:
                continue
            L += [f"### Bài toán: dự đoán `{key}` ({r['num_docs']} văn bản, {len(r['class_counts'])} lớp)",
                  _table(["Mô hình", "CV macro-F1", "Test macro-F1"],
                         [[m, f"{v['cv_f1_macro']} ± {v['cv_std']}", v["test_f1_macro"]] for m, v in r["models"].items()]),
                  f"\nMô hình tốt nhất: **{r['best_model']}**\n",
                  _table(["Lớp", "Precision", "Recall", "F1", "Support"],
                         [[lb, round(v["precision"], 3), round(v["recall"], 3), round(v["f1-score"], 3), int(v["support"])]
                          for lb, v in r["report"].items() if isinstance(v, dict) and lb not in ("macro avg", "weighted avg")]),
                  "", *[f"- **{lb}**: {', '.join(fs)}" for lb, fs in r["top_features"].items()],
                  "", f"![cm]({r['figures']['confusion']})", ""]

    n = results.get("ner")
    if n:
        L += [f"## 6. Nhận dạng thực thể (mẫu {n['sample_docs']} văn bản)",
              _table(["Loại", "Thực thể phổ biến"], [[t, ", ".join(f"{e} ({c})" for e, c in v[:15])] for t, v in n["top"].items()]),
              "", f"![ner]({n['figures']['top_entities']})", ""]

    path = REPORTS_DIR / "REPORT.md"
    path.write_text("\n".join(L), encoding="utf-8")
    return str(path)
