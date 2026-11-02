/**
 * BM25 (Okapi) - truy hồi theo từ khóa (sparse retrieval).
 * Bổ trợ cho dense retrieval ở các truy vấn chứa tên riêng, thuật ngữ Hán-Việt, Pāli, số hiệu kinh...
 * Port của pipeline/retrieval/bm25.py.
 */
import { bm25Tokenize } from "../text/normalize";
import type { Ranking } from "../types";

export class BM25Index {
  /** term -> mảng phẳng [doc0, tf0, doc1, tf1, ...] (gọn bộ nhớ hơn mảng các cặp) */
  private postings = new Map<string, number[]>();
  private docLen: Uint32Array;
  private avgdl: number;
  readonly n: number;

  constructor(texts: string[], private k1 = 1.2, private b = 0.75) {
    this.n = texts.length;
    this.docLen = new Uint32Array(this.n);
    let total = 0;
    texts.forEach((text, i) => {
      const tf = new Map<string, number>();
      for (const t of bm25Tokenize(text)) tf.set(t, (tf.get(t) ?? 0) + 1);
      let len = 0;
      for (const [term, f] of tf) {
        len += f;
        let list = this.postings.get(term);
        if (!list) this.postings.set(term, (list = []));
        list.push(i, f);
      }
      this.docLen[i] = len;
      total += len;
    });
    this.avgdl = total / Math.max(1, this.n);
  }

  private idf(df: number): number {
    return Math.log(1 + (this.n - df + 0.5) / (df + 0.5));
  }

  search(query: string, k = 30): Ranking {
    const scores = new Map<number, number>();
    for (const term of new Set(bm25Tokenize(query))) {
      const list = this.postings.get(term);
      if (!list) continue;
      const idf = this.idf(list.length / 2);
      for (let p = 0; p < list.length; p += 2) {
        const i = list[p];
        const f = list[p + 1];
        const denom = f + this.k1 * (1 - this.b + (this.b * this.docLen[i]) / this.avgdl);
        scores.set(i, (scores.get(i) ?? 0) + (idf * f * (this.k1 + 1)) / denom);
      }
    }
    return [...scores.entries()].sort((a, b) => b[1] - a[1]).slice(0, k);
  }
}
