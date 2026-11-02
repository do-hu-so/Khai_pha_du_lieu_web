/**
 * LLM Reranker (pointwise trong 1 lần gọi): mô hình nhỏ của Groq chấm điểm mức độ liên quan
 * 0-10 cho từng ứng viên so với câu hỏi. Chính xác hơn RRF vì "đọc hiểu" cả câu hỏi lẫn đoạn văn
 * (vai trò giống cross-encoder) nhưng không cần chạy mô hình rerank riêng trên server.
 */
import { RAG_CONFIG } from "../config";
import { chatComplete } from "../generation/groq";
import type { Candidate } from "../types";

const SYSTEM = `Bạn là bộ chấm điểm mức độ liên quan cho hệ thống tìm kiếm tài liệu Phật giáo tiếng Việt.
Với mỗi đoạn văn, chấm điểm từ 0 đến 10 cho biết đoạn văn hữu ích thế nào để TRẢ LỜI câu hỏi:
10 = trả lời trực tiếp; 6-8 = chứa thông tin liên quan quan trọng; 3-5 = liên quan một phần; 0-2 = không liên quan.
Chỉ trả về JSON dạng {"scores":[{"id":1,"score":7}, ...]} cho TẤT CẢ các đoạn.`;

export async function llmRerank(query: string, cands: Candidate[]): Promise<Candidate[]> {
  if (cands.length === 0) return cands;
  const { snippetChars } = RAG_CONFIG.reranking;
  const passages = cands
    .map((c, i) => `[${i + 1}] (${c.chunk.title})\n${c.chunk.text.slice(0, snippetChars).replace(/\s+/g, " ")}`)
    .join("\n\n");
  const raw = await chatComplete(
    [
      { role: "system", content: SYSTEM },
      { role: "user", content: `Câu hỏi: ${query}\n\nCác đoạn văn:\n${passages}` },
    ],
    { model: RAG_CONFIG.groq.fastModel, temperature: 0, maxTokens: 1500, json: true },
  );
  const parsed = JSON.parse(raw) as { scores?: Array<{ id: number; score: number }> };
  for (const s of parsed.scores ?? []) {
    const c = cands[Number(s.id) - 1];
    if (c) c.rerankScore = Math.max(0, Math.min(10, Number(s.score) || 0));
  }
  // Ứng viên LLM bỏ sót -> điểm 0. Hòa điểm -> giữ thứ tự RRF.
  return cands
    .map((c, i) => ({ c, i }))
    .sort((a, b) => (b.c.rerankScore ?? 0) - (a.c.rerankScore ?? 0) || a.i - b.i)
    .map((x) => x.c);
}
