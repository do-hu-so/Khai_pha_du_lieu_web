/**
 * Dense retrieval: tìm chunk có vector gần câu hỏi nhất (cosine = tích vô hướng vì đã chuẩn hóa L2).
 * Quét toàn bộ (brute-force) - với vài chục nghìn chunk x 384 chiều chỉ mất vài ms,
 * không cần vector database.
 */
import type { Ranking } from "../types";

export function denseSearch(vectors: Float32Array, dim: number, query: Float32Array, k = 30): Ranking {
  const n = vectors.length / dim;
  const top: Ranking = []; // giữ k phần tử tốt nhất, sắp giảm dần
  for (let i = 0; i < n; i++) {
    let s = 0;
    const off = i * dim;
    for (let j = 0; j < dim; j++) s += vectors[off + j] * query[j];
    if (top.length < k || s > top[top.length - 1][1]) {
      let pos = top.length;
      while (pos > 0 && top[pos - 1][1] < s) pos--;
      top.splice(pos, 0, [i, s]);
      if (top.length > k) top.pop();
    }
  }
  return top;
}

export function cosine(vectors: Float32Array, dim: number, a: number, b: number): number {
  let s = 0;
  for (let j = 0; j < dim; j++) s += vectors[a * dim + j] * vectors[b * dim + j];
  return s;
}
