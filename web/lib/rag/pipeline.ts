/**
 * BỘ ĐIỀU PHỐI RAG - ghép các bước:
 *
 *   câu hỏi ──► [1] viết lại câu hỏi (query/rewrite.ts)
 *           ──► [2] embedding câu hỏi (embedding/query-embedder.ts)
 *           ──► [3] truy hồi lai Dense + BM25 + RRF (retrieval/)
 *           ──► [4] xếp hạng lại LLM / MMR (reranking/)
 *           ──► [5] dựng prompt + sinh câu trả lời bằng Groq (generation/)
 */
import { RAG_CONFIG } from "./config";
import { embedQuery } from "./embedding/query-embedder";
import { buildMessages } from "./generation/prompt";
import type { LlmMessage } from "./generation/groq";
import { getIndex } from "./index/store";
import { rewriteQuery } from "./query/rewrite";
import { rerank, type RerankStrategy } from "./reranking";
import { hybridSearch } from "./retrieval/hybrid";
import type { Candidate, ChatMessage, RagTrace, SourceRef } from "./types";

export interface RetrievalOptions {
  /** ghi đè chiến lược rerank (mặc định theo RAG_CONFIG) */
  reranker?: RerankStrategy;
  /** có viết lại câu hỏi theo lịch sử hội thoại không */
  rewrite?: boolean;
}

export interface RetrievalResult {
  searchQuery: string;
  selected: Candidate[];
  sources: SourceRef[];
  trace: RagTrace;
}

const hasGroq = () => RAG_CONFIG.groq.apiKey.length > 0;

export async function retrieve(
  question: string,
  history: ChatMessage[] = [],
  opts: RetrievalOptions = {},
): Promise<RetrievalResult> {
  const timings: Record<string, number> = {};
  const tick = async <T>(name: string, fn: () => Promise<T> | T): Promise<T> => {
    const t0 = Date.now();
    try {
      return await fn();
    } finally {
      timings[name] = Date.now() - t0;
    }
  };

  const store = await tick("load_index", getIndex);

  // [1] Viết lại câu hỏi nối tiếp thành câu hỏi độc lập
  const searchQuery =
    opts.rewrite !== false && history.length > 0 && hasGroq()
      ? await tick("rewrite", () => rewriteQuery(history, question))
      : question;

  // [2] Embedding câu hỏi - nếu lỗi (vd không tải được mô hình) vẫn chạy được bằng BM25
  let queryVec: Float32Array | null = null;
  await tick("embed_query", async () => {
    try {
      queryVec = await embedQuery(searchQuery, store.manifest.web_model_name, store.manifest.query_prefix);
    } catch (e) {
      console.error("[embedding] lỗi, chỉ dùng BM25:", e);
    }
  });

  // [3] Hybrid retrieval
  const candidates = await tick("retrieve", () => hybridSearch(store, searchQuery, queryVec));

  // [4] Reranking (chưa có GROQ_API_KEY thì không thể dùng LLM reranker -> giữ thứ tự RRF)
  const wanted = opts.reranker ?? RAG_CONFIG.reranking.strategy;
  const strategy = wanted === "llm" && !hasGroq() ? "none" : wanted;
  const { ranked, selected, strategy: used } = await tick("rerank", () =>
    rerank(store, searchQuery, queryVec, candidates, strategy),
  );

  const selectedIds = new Set(selected.map((c) => c.chunk.id));
  const sources: SourceRef[] = selected.map((c, i) => ({
    n: i + 1,
    title: c.chunk.title,
    url: c.chunk.url,
    source: c.chunk.source,
    sourceName: c.chunk.source_name,
    category: c.chunk.category,
    snippet: c.chunk.text.slice(0, 280),
  }));

  return {
    searchQuery,
    selected,
    sources,
    trace: {
      originalQuery: question,
      searchQuery,
      embeddingOk: queryVec !== null,
      timingsMs: timings,
      reranker: used,
      candidates: ranked.map((c) => ({
        id: c.chunk.id,
        title: c.chunk.title,
        source: c.chunk.source,
        denseRank: c.denseRank,
        bm25Rank: c.bm25Rank,
        rrf: +c.rrf.toFixed(5),
        rerankScore: c.rerankScore,
        selected: selectedIds.has(c.chunk.id),
      })),
    },
  };
}

/** Chuẩn bị đầy đủ cho bước sinh: kết quả truy hồi + danh sách message gửi LLM. */
export async function prepareAnswer(
  question: string,
  history: ChatMessage[],
): Promise<RetrievalResult & { llmMessages: LlmMessage[] }> {
  const r = await retrieve(question, history);
  return { ...r, llmMessages: buildMessages(history, question, r.selected) };
}
