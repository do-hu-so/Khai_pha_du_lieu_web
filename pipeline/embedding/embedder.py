"""Mô hình embedding (sentence-transformers).

Mặc định: intfloat/multilingual-e5-small (384 chiều, đa ngôn ngữ, hỗ trợ tốt tiếng Việt).
Họ mô hình E5 yêu cầu tiền tố: "passage: " cho văn bản trong kho, "query: " cho câu hỏi.
"""
from __future__ import annotations

import logging

import numpy as np

log = logging.getLogger(__name__)


class Embedder:
    def __init__(self, model_name: str, passage_prefix: str = "passage: ", query_prefix: str = "query: ",
                 max_seq_length: int = 512, normalize: bool = True, device: str | None = None):
        from sentence_transformers import SentenceTransformer

        log.info("Tải mô hình embedding: %s", model_name)
        self.model = SentenceTransformer(model_name, device=device)
        self.model.max_seq_length = max_seq_length
        self.model_name = model_name
        self.passage_prefix, self.query_prefix = passage_prefix, query_prefix
        self.normalize = normalize

    @property
    def dim(self) -> int:
        return self.model.get_sentence_embedding_dimension()

    def embed_passages(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        return self.model.encode(
            [self.passage_prefix + t for t in texts], batch_size=batch_size,
            normalize_embeddings=self.normalize, show_progress_bar=True, convert_to_numpy=True,
        ).astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        return self.model.encode(
            [self.query_prefix + query], normalize_embeddings=self.normalize, convert_to_numpy=True,
        )[0].astype(np.float32)


def passage_text(chunk: dict) -> str:
    """Văn bản đưa vào embedding: tiêu đề + nội dung chunk (tiêu đề giúp định vị ngữ cảnh)."""
    return f"{chunk['title']}\n{chunk['text']}"
