/**
 * Embedding câu hỏi lúc truy vấn bằng transformers.js (ONNX Runtime, chạy ngay trong serverless function).
 *
 * Kho văn bản đã được embed SẴN bằng Python (sentence-transformers) với cùng mô hình
 * (intfloat/multilingual-e5-small <-> Xenova/multilingual-e5-small là bản ONNX của nó),
 * nên vector câu hỏi và vector văn bản nằm cùng một không gian.
 */
import { RAG_CONFIG } from "../config";

type Extractor = (
  text: string | string[],
  opts: { pooling: "mean"; normalize: boolean },
) => Promise<{ data: Float32Array | number[] }>;

let extractorPromise: Promise<Extractor> | null = null;

async function getExtractor(modelName: string): Promise<Extractor> {
  if (!extractorPromise) {
    extractorPromise = (async () => {
      const t0 = Date.now();
      const { pipeline, env } = await import("@huggingface/transformers");
      env.cacheDir = RAG_CONFIG.embedding.cacheDir;
      env.allowLocalModels = false;
      const extractor = await pipeline("feature-extraction", modelName, { dtype: RAG_CONFIG.embedding.dtype });
      console.log(`[embedding] nạp mô hình ${modelName} trong ${Date.now() - t0}ms`);
      return extractor as unknown as Extractor;
    })().catch((e) => {
      extractorPromise = null;
      throw e;
    });
  }
  return extractorPromise;
}

/** Trả về vector đã chuẩn hóa L2 của câu hỏi (mean pooling - giống cấu hình E5 ở Python). */
export async function embedQuery(query: string, modelName: string, prefix = "query: "): Promise<Float32Array> {
  const extractor = await getExtractor(modelName);
  const out = await extractor(prefix + query, { pooling: "mean", normalize: true });
  return out.data instanceof Float32Array ? out.data : Float32Array.from(out.data);
}

/** Gọi sớm để nạp mô hình (giảm độ trễ request đầu tiên). */
export function warmupEmbedder(modelName: string): void {
  getExtractor(modelName).catch((e) => console.error("[embedding] warmup lỗi:", e));
}
