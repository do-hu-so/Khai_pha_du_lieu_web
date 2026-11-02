/**
 * Cấu hình RAG - mọi tham số điều chỉnh được đều tập trung ở đây (ghi đè bằng biến môi trường).
 */
import path from "node:path";

const num = (v: string | undefined, d: number) => (v !== undefined && v !== "" && !isNaN(+v) ? +v : d);

export const RAG_CONFIG = {
  /** Thư mục index do pipeline Python sinh ra (python -m pipeline embed) */
  indexDir: path.join(process.cwd(), "data", "index"),

  embedding: {
    /** Thư mục cache mô hình ONNX. Trên Vercel chỉ /tmp được phép ghi. */
    cacheDir: process.env.VERCEL ? "/tmp/hf-cache" : path.join(process.cwd(), ".cache"),
    /** q8 = mô hình lượng tử hóa 8-bit (~118MB) - nhanh, sai khác rất nhỏ so với bản fp32 dùng ở Python */
    dtype: (process.env.EMBEDDING_DTYPE ?? "q8") as "q8" | "fp32" | "fp16",
  },

  retrieval: {
    denseTopK: num(process.env.RAG_DENSE_TOPK, 30),
    bm25TopK: num(process.env.RAG_BM25_TOPK, 30),
    /** hằng số k trong Reciprocal Rank Fusion */
    rrfK: 60,
    denseWeight: num(process.env.RAG_DENSE_WEIGHT, 1.0),
    bm25Weight: num(process.env.RAG_BM25_WEIGHT, 1.0),
    /** số ứng viên sau hợp nhất được đưa vào bước reranking */
    candidates: num(process.env.RAG_CANDIDATES, 16),
    /** tối đa bao nhiêu chunk từ cùng 1 văn bản (tránh ngữ cảnh lặp) */
    maxChunksPerDoc: 2,
  },

  reranking: {
    strategy: (process.env.RERANKER ?? "llm") as "llm" | "mmr" | "none",
    /** cắt nội dung mỗi ứng viên khi gửi cho LLM chấm điểm (tiết kiệm token) */
    snippetChars: 400,
    /** ứng viên có điểm liên quan (0-10) thấp hơn ngưỡng sẽ bị loại */
    minScore: num(process.env.RERANK_MIN_SCORE, 3),
    mmrLambda: 0.7,
  },

  context: {
    /** số chunk đưa vào prompt sinh câu trả lời */
    chunks: num(process.env.RAG_CONTEXT_CHUNKS, 6),
    historyTurns: 6,
  },

  groq: {
    apiKey: process.env.GROQ_API_KEY ?? "",
    baseUrl: "https://api.groq.com/openai/v1",
    /** model sinh câu trả lời (mạnh nhất). Danh sách model: https://console.groq.com/docs/models */
    model: process.env.GROQ_MODEL ?? "openai/gpt-oss-120b",
    /** model nhanh cho viết lại câu hỏi + reranking (cần hỗ trợ JSON mode) */
    fastModel: process.env.GROQ_FAST_MODEL ?? "qwen/qwen3.8-27b",
    /** thứ tự model dự phòng khi model chính vượt hạn mức (mỗi model có hạn mức token/phút riêng) */
    fallbackModels: (process.env.GROQ_FALLBACK_MODELS ?? "openai/gpt-oss-20b,qwen/qwen3.8-27b")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
    temperature: 0.2,
    /** giới hạn độ dài câu trả lời - Groq tính cả con số này vào hạn mức token/phút */
    maxTokens: num(process.env.GROQ_MAX_TOKENS, 1024),
  },
} as const;
