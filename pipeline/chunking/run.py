"""Bước 4 - CHUNKING: data/processed/corpus.jsonl -> data/chunks/chunks.jsonl"""
from __future__ import annotations

import logging
import statistics

from ..config import CHUNKS_FILE, CORPUS_FILE, ensure_dirs, pipeline_config
from ..utils.io import read_jsonl, write_jsonl
from .chunker import TextChunker

log = logging.getLogger(__name__)


def run() -> None:
    ensure_dirs()
    cfg = pipeline_config()["chunking"]
    chunker = TextChunker(cfg["chunk_size"], cfg["chunk_overlap"], cfg["min_chunk_chars"])
    chunks, n_docs = [], 0
    for doc in read_jsonl(CORPUS_FILE):
        n_docs += 1
        for i, text in enumerate(chunker.split(doc["text"])):
            chunks.append({
                "id": f"{doc['doc_id']}#{i}",
                "doc_id": doc["doc_id"],
                "position": i,
                "title": doc["title"],
                "url": doc["url"],
                "source": doc["source"],
                "source_name": doc["source_name"],
                "category": doc["category"],
                "text": text,
            })
    write_jsonl(CHUNKS_FILE, chunks)
    lens = [len(c["text"]) for c in chunks] or [0]
    log.info("Chunking: %d văn bản -> %d chunk (độ dài TB %.0f, trung vị %.0f, max %d ký tự)",
             n_docs, len(chunks), statistics.mean(lens), statistics.median(lens), max(lens))
    log.info("-> %s", CHUNKS_FILE)
