/**
 * Maximal Marginal Relevance: chọn lần lượt ứng viên vừa liên quan tới câu hỏi
 * vừa ít trùng lặp với các ứng viên đã chọn.
 *     MMR = λ · sim(q, d) − (1 − λ) · max_{s ∈ đã chọn} sim(d, s)
 * Không tốn lời gọi LLM - dùng khi muốn rerank nhanh / miễn phí.
 */
import { RAG_CONFIG } from "../config";
import type { IndexStore } from "../index/store";
import { cosine } from "../retrieval/dense";
import type { Candidate } from "../types";

export function mmrRerank(store: IndexStore, queryVec: Float32Array | null, cands: Candidate[], k: number): Candidate[] {
  if (!queryVec || cands.length <= 1) return cands;
  const { dim } = store.manifest;
  const lambda = RAG_CONFIG.reranking.mmrLambda;
  const rel = cands.map((c) => {
    let s = 0;
    for (let j = 0; j < dim; j++) s += store.vectors[c.index * dim + j] * queryVec[j];
    return s;
  });
  const chosen: number[] = [];
  const left = new Set(cands.map((_, i) => i));
  while (chosen.length < Math.min(k, cands.length)) {
    let best = -1;
    let bestScore = -Infinity;
    for (const i of left) {
      const red = chosen.length ? Math.max(...chosen.map((j) => cosine(store.vectors, dim, cands[i].index, cands[j].index))) : 0;
      const score = lambda * rel[i] - (1 - lambda) * red;
      if (score > bestScore) [best, bestScore] = [i, score];
    }
    chosen.push(best);
    left.delete(best);
  }
  return [...chosen, ...left].map((i, rank) => ({ ...cands[i], rerankScore: rank < chosen.length ? +(rel[i] * 10).toFixed(2) : undefined }));
}
