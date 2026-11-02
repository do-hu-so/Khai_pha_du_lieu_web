/**
 * Bước RERANKING: sắp xếp lại các ứng viên từ hybrid retrieval rồi chọn ngữ cảnh cuối cùng.
 * Chiến lược cấu hình qua biến môi trường RERANKER = llm | mmr | none.
 */
import { RAG_CONFIG } from "../config";
import type { IndexStore } from "../index/store";
import type { Candidate } from "../types";
import { llmRerank } from "./llm-reranker";
import { mmrRerank } from "./mmr";

export type RerankStrategy = "llm" | "mmr" | "none";

export async function rerank(
  store: IndexStore,
  query: string,
  queryVec: Float32Array | null,
  cands: Candidate[],
  strategy: RerankStrategy = RAG_CONFIG.reranking.strategy,
): Promise<{ ranked: Candidate[]; selected: Candidate[]; strategy: string }> {
  const k = RAG_CONFIG.context.chunks;

  if (strategy === "llm") {
    try {
      const ranked = await llmRerank(query, cands);
      let selected = ranked.filter((c) => (c.rerankScore ?? 0) >= RAG_CONFIG.reranking.minScore).slice(0, k);
      // Không ứng viên nào đạt ngưỡng: vẫn đưa 2 đoạn tốt nhất để LLM tự kết luận "không đủ thông tin"
      if (selected.length === 0) selected = ranked.slice(0, 2);
      return { ranked, selected, strategy };
    } catch (e) {
      console.error("[rerank] LLM rerank lỗi, dùng thứ tự RRF:", e);
      return { ranked: cands, selected: cands.slice(0, k), strategy: "none (llm lỗi)" };
    }
  }
  if (strategy === "mmr") {
    const ranked = mmrRerank(store, queryVec, cands, k);
    return { ranked, selected: ranked.slice(0, k), strategy };
  }
  return { ranked: cands, selected: cands.slice(0, k), strategy: "none" };
}
