/**
 * Hybrid retrieval = Dense (ngữ nghĩa) + BM25 (từ khóa), hợp nhất bằng Reciprocal Rank Fusion:
 *     RRF(d) = Σ  w_i / (k + rank_i(d))
 * RRF chỉ dùng thứ hạng nên không cần chuẩn hóa thang điểm khác nhau của 2 phương pháp.
 */
import { RAG_CONFIG } from "../config";
import type { IndexStore } from "../index/store";
import type { Candidate, Ranking } from "../types";
import { denseSearch } from "./dense";

export function rrfFuse(store: IndexStore, dense: Ranking, bm25: Ranking): Candidate[] {
  const { rrfK, denseWeight, bm25Weight } = RAG_CONFIG.retrieval;
  const fused = new Map<number, Candidate>();
  const get = (index: number) => {
    let c = fused.get(index);
    if (!c) fused.set(index, (c = { index, chunk: store.chunks[index], rrf: 0 }));
    return c;
  };
  dense.forEach(([index, score], r) => {
    const c = get(index);
    c.rrf += denseWeight / (rrfK + r + 1);
    c.denseRank = r + 1;
    c.denseScore = score;
  });
  bm25.forEach(([index, score], r) => {
    const c = get(index);
    c.rrf += bm25Weight / (rrfK + r + 1);
    c.bm25Rank = r + 1;
    c.bm25Score = score;
  });
  return [...fused.values()].sort((a, b) => b.rrf - a.rrf);
}

/** Giới hạn số chunk từ cùng 1 văn bản để ngữ cảnh đa dạng hơn. */
export function limitPerDoc(cands: Candidate[], maxPerDoc: number): Candidate[] {
  const count = new Map<string, number>();
  return cands.filter((c) => {
    const n = count.get(c.chunk.doc_id) ?? 0;
    count.set(c.chunk.doc_id, n + 1);
    return n < maxPerDoc;
  });
}

export function hybridSearch(store: IndexStore, query: string, queryVec: Float32Array | null): Candidate[] {
  const cfg = RAG_CONFIG.retrieval;
  const dense = queryVec ? denseSearch(store.vectors, store.manifest.dim, queryVec, cfg.denseTopK) : [];
  const bm25 = store.bm25.search(query, cfg.bm25TopK);
  return limitPerDoc(rrfFuse(store, dense, bm25), cfg.maxChunksPerDoc).slice(0, cfg.candidates);
}
