/**
 * Kho index: nạp manifest + chunks + ma trận embedding (tính sẵn bằng Python) vào bộ nhớ.
 * Nạp 1 lần / instance serverless, các request sau dùng lại (cache ở cấp module).
 */
import fs from "node:fs/promises";
import path from "node:path";
import { RAG_CONFIG } from "../config";
import { BM25Index } from "../retrieval/bm25";
import type { Chunk, Manifest } from "../types";

export interface IndexStore {
  manifest: Manifest;
  chunks: Chunk[];
  /** ma trận phẳng [numChunks * dim], hàng i = vector của chunks[i] (đã chuẩn hóa L2) */
  vectors: Float32Array;
  bm25: BM25Index;
}

let storePromise: Promise<IndexStore> | null = null;

async function load(): Promise<IndexStore> {
  const dir = RAG_CONFIG.indexDir;
  const t0 = Date.now();
  const [manifestRaw, chunksRaw, vecBuf] = await Promise.all([
    fs.readFile(path.join(dir, "manifest.json"), "utf-8"),
    fs.readFile(path.join(dir, "chunks.json"), "utf-8"),
    fs.readFile(path.join(dir, "embeddings.f32")),
  ]);
  const manifest = JSON.parse(manifestRaw) as Manifest;
  const chunks = JSON.parse(chunksRaw) as Chunk[];
  // Copy sang ArrayBuffer riêng để đảm bảo căn lề 4 byte cho Float32Array
  const vectors = new Float32Array(vecBuf.buffer.slice(vecBuf.byteOffset, vecBuf.byteOffset + vecBuf.byteLength));
  if (vectors.length !== chunks.length * manifest.dim) {
    throw new Error(
      `Index không khớp: ${vectors.length} giá trị != ${chunks.length} chunk x ${manifest.dim} chiều. Hãy chạy lại "python -m pipeline embed".`,
    );
  }
  const bm25 = new BM25Index(chunks.map((c) => `${c.title}\n${c.text}`));
  console.log(`[index] nạp ${chunks.length} chunk (${manifest.dim} chiều) trong ${Date.now() - t0}ms`);
  return { manifest, chunks, vectors, bm25 };
}

export function getIndex(): Promise<IndexStore> {
  if (!storePromise) {
    storePromise = load().catch((e) => {
      storePromise = null; // cho phép thử lại ở request sau
      throw e;
    });
  }
  return storePromise;
}
