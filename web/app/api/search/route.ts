/**
 * POST /api/search - chỉ chạy phần TRUY HỒI (không sinh câu trả lời) để kiểm tra/so sánh.
 * Body: { "query": "...", "reranker": "llm" | "mmr" | "none" }
 * Không cần GROQ_API_KEY nếu reranker = "mmr" hoặc "none".
 */
import { retrieve } from "@/lib/rag/pipeline";
import type { RerankStrategy } from "@/lib/rag/reranking";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

export async function POST(req: Request) {
  const { query, reranker } = (await req.json().catch(() => ({}))) as { query?: string; reranker?: RerankStrategy };
  if (!query?.trim()) return Response.json({ error: "Thiếu query" }, { status: 400 });
  try {
    const r = await retrieve(query.trim().slice(0, 1000), [], { reranker });
    return Response.json({
      query: r.searchQuery,
      trace: r.trace,
      results: r.selected.map((c, i) => ({
        rank: i + 1,
        id: c.chunk.id,
        title: c.chunk.title,
        url: c.chunk.url,
        source: c.chunk.source,
        category: c.chunk.category,
        denseScore: c.denseScore,
        bm25Score: c.bm25Score,
        rrf: c.rrf,
        rerankScore: c.rerankScore,
        text: c.chunk.text,
      })),
    });
  } catch (e) {
    console.error("[search]", e);
    return Response.json({ error: e instanceof Error ? e.message : String(e) }, { status: 500 });
  }
}
