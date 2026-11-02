"""Đánh giá định lượng bước truy hồi: so sánh BM25 / Dense / Hybrid.

Bộ câu hỏi: data/eval/retrieval_questions.jsonl, mỗi dòng {"question", "relevant": [chuỗi con của tiêu đề]}.
Một văn bản được coi là LIÊN QUAN nếu tiêu đề chứa 1 trong các chuỗi "relevant" (không phân biệt hoa/thường).
Kết quả xếp hạng ở mức chunk được gộp về mức văn bản (giữ thứ hạng đầu tiên của mỗi văn bản).

    python -m pipeline evaluate
Chỉ số: Hit@1, Hit@3, Hit@5 (tỉ lệ câu hỏi có văn bản liên quan trong top-k), MRR@10.
"""
from __future__ import annotations

import time

from ..config import DATA_DIR, INDEX_DIR, REPORTS_DIR
from ..embedding.build_index import load_index
from ..embedding.embedder import Embedder
from ..nlp.normalize import normalize_text
from ..utils.io import read_jsonl, write_json
from .bm25 import BM25Index
from .hybrid import dense_search, rrf_fuse

EVAL_FILE = DATA_DIR / "eval" / "retrieval_questions.jsonl"


def _doc_ranking(chunk_ranking: list[int], chunks: list[dict], k: int = 10) -> list[str]:
    titles, seen = [], set()
    for idx in chunk_ranking:
        doc = chunks[idx]["doc_id"]
        if doc not in seen:
            seen.add(doc)
            titles.append(chunks[idx]["title"])
        if len(titles) == k:
            break
    return titles


def run(candidates: int = 50) -> dict:
    manifest, chunks, vectors = load_index(INDEX_DIR)
    questions = list(read_jsonl(EVAL_FILE))
    embedder = Embedder(manifest["model_name"], manifest["passage_prefix"], manifest["query_prefix"])
    bm25 = BM25Index([f"{c['title']}\n{c['text']}" for c in chunks])

    methods = {
        "BM25": lambda q, v: [i for i, _ in bm25.search(q, candidates)],
        "Dense": lambda q, v: [i for i, _ in dense_search(vectors, v, candidates)],
        "Hybrid (RRF)": lambda q, v: [f["index"] for f in rrf_fuse(
            {"dense": dense_search(vectors, v, candidates), "bm25": bm25.search(q, candidates)})],
    }
    per_question, totals = [], {m: {"hit@1": 0, "hit@3": 0, "hit@5": 0, "mrr@10": 0.0, "ms": 0.0} for m in methods}
    for item in questions:
        q = item["question"]
        rel = [normalize_text(r).lower() for r in item["relevant"]]
        qvec = embedder.embed_query(q)
        row = {"question": q}
        for name, fn in methods.items():
            t0 = time.time()
            titles = _doc_ranking(fn(q, qvec), chunks)
            totals[name]["ms"] += (time.time() - t0) * 1000
            rank = next((i + 1 for i, t in enumerate(titles) if any(r in normalize_text(t).lower() for r in rel)), None)
            row[name] = rank
            for k in (1, 3, 5):
                totals[name][f"hit@{k}"] += int(rank is not None and rank <= k)
            totals[name]["mrr@10"] += 1 / rank if rank else 0.0
        per_question.append(row)

    n = len(questions)
    summary = {m: {k: round(v / n, 3) if k != "ms" else round(v / n, 1) for k, v in t.items()} for m, t in totals.items()}
    print(f"\nĐánh giá truy hồi trên {n} câu hỏi ({manifest['num_chunks']} chunk)\n")
    print(f"{'Phương pháp':<14} {'Hit@1':>6} {'Hit@3':>6} {'Hit@5':>6} {'MRR@10':>7} {'ms/câu':>7}")
    for m, s in summary.items():
        print(f"{m:<14} {s['hit@1']:>6} {s['hit@3']:>6} {s['hit@5']:>6} {s['mrr@10']:>7} {s['ms']:>7}")
    print("\nThứ hạng văn bản liên quan đầu tiên theo từng câu hỏi (- = không có trong top 10):")
    for row in per_question:
        ranks = "  ".join(f"{m.split()[0]}={row[m] or '-'}" for m in methods)
        print(f"  {ranks:<28} {row['question'][:70]}")
    result = {"num_questions": n, "summary": summary, "per_question": per_question}
    write_json(REPORTS_DIR / "retrieval_eval.json", result)
    return result
