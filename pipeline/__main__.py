"""Điểm vào dòng lệnh của pipeline.

    python -m pipeline crawl [--only phatgiao vbeta] [--max-articles 50] [--fresh]
    python -m pipeline preprocess
    python -m pipeline mine [--tasks stats keywords topics clustering classification ner]
    python -m pipeline chunk
    python -m pipeline embed
    python -m pipeline search "câu hỏi" [--mode hybrid|dense|bm25] [-k 5]
    python -m pipeline evaluate     # đánh giá truy hồi trên data/eval/retrieval_questions.jsonl
    python -m pipeline all          # crawl -> preprocess -> mine -> chunk -> embed
"""
from __future__ import annotations

import argparse
import logging
import sys


def main(argv: list[str] | None = None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
                        datefmt="%H:%M:%S")
    for noisy in ("trafilatura", "urllib3", "httpx", "sentence_transformers", "htmldate"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    p = argparse.ArgumentParser(prog="python -m pipeline", description="Kho văn bản Phật giáo + RAG")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("crawl", help="Bước 1: thu thập dữ liệu")
    c.add_argument("--only", nargs="*", help="chỉ crawl các nguồn này (id trong sources.yaml)")
    c.add_argument("--max-articles", type=int, help="ghi đè max_articles cho mọi nguồn")
    c.add_argument("--fresh", action="store_true", help="xóa dữ liệu thô cũ, crawl lại từ đầu")
    sub.add_parser("preprocess", help="Bước 2: làm sạch, lọc, khử trùng lặp, gán chủ đề")
    m = sub.add_parser("mine", help="Bước 3: khai phá văn bản & XLNNTN")
    m.add_argument("--tasks", nargs="*", help="stats keywords topics clustering classification ner")
    m.add_argument("--resegment", action="store_true", help="tách từ lại (bỏ cache)")
    sub.add_parser("chunk", help="Bước 4: chia chunk")
    e = sub.add_parser("embed", help="Bước 5: embedding + lưu index (data/index -> web/data/index)")
    e.add_argument("--limit", type=int, help="chỉ embed N chunk đầu (thử nghiệm)")
    sub.add_parser("export", help="copy data/index -> web/data/index")
    s = sub.add_parser("search", help="thử truy hồi trên index")
    s.add_argument("query")
    s.add_argument("--mode", default="hybrid", choices=["hybrid", "dense", "bm25"])
    s.add_argument("-k", type=int, default=5)
    sub.add_parser("evaluate", help="đánh giá truy hồi BM25 / Dense / Hybrid (Hit@k, MRR)")
    sub.add_parser("all", help="chạy toàn bộ các bước 1-5")
    args = p.parse_args(argv)

    if args.cmd in ("crawl", "all"):
        from .crawling import run as crawl
        crawl.run(getattr(args, "only", None), getattr(args, "fresh", False), getattr(args, "max_articles", None))
    if args.cmd in ("preprocess", "all"):
        from .preprocessing import run as preprocess
        preprocess.run()
    if args.cmd in ("mine", "all"):
        from .mining import run as mine
        mine.run(getattr(args, "tasks", None), getattr(args, "resegment", False))
    if args.cmd in ("chunk", "all"):
        from .chunking import run as chunk
        chunk.run()
    if args.cmd in ("embed", "all"):
        from .embedding import build_index
        build_index.run(getattr(args, "limit", None))
    if args.cmd == "export":
        from .embedding.build_index import export_to_web
        export_to_web()
    if args.cmd == "search":
        from .retrieval import search
        search.run(args.query, args.mode, args.k)
    if args.cmd == "evaluate":
        from .retrieval import evaluate
        evaluate.run()


if __name__ == "__main__":
    main()
