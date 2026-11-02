/** Kiểu dữ liệu dùng chung cho toàn bộ pipeline RAG. */

/** 1 chunk trong index (do Python sinh ra: data/index/chunks.json). */
export interface Chunk {
  id: string;
  doc_id: string;
  position: number;
  title: string;
  url: string;
  source: string;
  source_name: string;
  category: string;
  text: string;
}

export interface Manifest {
  created_at: string;
  model_name: string;
  web_model_name: string;
  passage_prefix: string;
  query_prefix: string;
  dim: number;
  num_chunks: number;
  num_docs: number;
  normalized: boolean;
  by_source: Record<string, number>;
  by_category: Record<string, number>;
  sources: Record<string, string>;
}

/** Kết quả xếp hạng của 1 bộ truy hồi: [chỉ số chunk, điểm]. */
export type Ranking = Array<[index: number, score: number]>;

/** Ứng viên sau khi hợp nhất (và có thể đã rerank). */
export interface Candidate {
  index: number;
  chunk: Chunk;
  rrf: number;
  denseRank?: number;
  denseScore?: number;
  bm25Rank?: number;
  bm25Score?: number;
  rerankScore?: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

/** Nguồn trích dẫn gửi về giao diện. */
export interface SourceRef {
  n: number;
  title: string;
  url: string;
  source: string;
  sourceName: string;
  category: string;
  snippet: string;
}

/** Thông tin chẩn đoán từng bước - hiển thị ở bảng "Chi tiết truy hồi". */
export interface RagTrace {
  originalQuery: string;
  searchQuery: string;
  embeddingOk: boolean;
  timingsMs: Record<string, number>;
  candidates: Array<{
    id: string;
    title: string;
    source: string;
    denseRank?: number;
    bm25Rank?: number;
    rrf: number;
    rerankScore?: number;
    selected: boolean;
  }>;
  reranker: string;
  /** model Groq đã sinh câu trả lời (có thể là model dự phòng khi model chính quá tải) */
  generationModel?: string;
}
