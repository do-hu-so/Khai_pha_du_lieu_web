/** GET /api/health - thông tin index + cấu hình (hiển thị ở chân trang, dùng để kiểm tra deploy). */
import { RAG_CONFIG } from "@/lib/rag/config";
import { getIndex } from "@/lib/rag/index/store";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const { manifest } = await getIndex();
    return Response.json({
      ok: true,
      index: {
        createdAt: manifest.created_at,
        numChunks: manifest.num_chunks,
        numDocs: manifest.num_docs,
        dim: manifest.dim,
        model: manifest.web_model_name,
        bySource: manifest.by_source,
        sources: manifest.sources,
        byCategory: manifest.by_category,
      },
      config: {
        groqConfigured: RAG_CONFIG.groq.apiKey.length > 0,
        model: RAG_CONFIG.groq.model,
        fastModel: RAG_CONFIG.groq.fastModel,
        reranker: RAG_CONFIG.reranking.strategy,
        contextChunks: RAG_CONFIG.context.chunks,
      },
    });
  } catch (e) {
    return Response.json({ ok: false, error: e instanceof Error ? e.message : String(e) }, { status: 500 });
  }
}
