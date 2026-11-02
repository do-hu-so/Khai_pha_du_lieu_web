import type { RagTrace } from "@/lib/rag/types";

const STEP_LABELS: Record<string, string> = {
  load_index: "Nạp index",
  rewrite: "Viết lại câu hỏi",
  embed_query: "Embedding câu hỏi",
  retrieve: "Truy hồi lai",
  rerank: "Xếp hạng lại",
  total: "Tổng (gồm sinh câu trả lời)",
};

/** Bảng chẩn đoán: thứ hạng của từng ứng viên qua các bước Dense / BM25 / RRF / Rerank. */
export default function TraceTable({ trace }: { trace: RagTrace }) {
  return (
    <details className="trace">
      <summary>
        Chi tiết truy hồi · reranker: {trace.reranker}
        {trace.generationModel ? ` · model trả lời: ${trace.generationModel}` : ""}
      </summary>
      {trace.searchQuery !== trace.originalQuery && (
        <p>
          Câu hỏi sau khi viết lại: <em>{trace.searchQuery}</em>
        </p>
      )}
      {!trace.embeddingOk && <p className="error">Không embedding được câu hỏi - chỉ dùng BM25.</p>}
      <p className="timings">
        {Object.entries(trace.timingsMs).map(([k, v]) => (
          <span key={k}>
            {STEP_LABELS[k] ?? k}: <b>{v} ms</b>
          </span>
        ))}
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Đoạn văn</th>
              <th title="Thứ hạng theo độ tương đồng vector">Dense</th>
              <th title="Thứ hạng theo BM25">BM25</th>
              <th title="Điểm Reciprocal Rank Fusion">RRF</th>
              <th title="Điểm liên quan 0-10 do reranker chấm">Rerank</th>
            </tr>
          </thead>
          <tbody>
            {trace.candidates.map((c, i) => (
              <tr key={c.id} className={c.selected ? "selected" : undefined}>
                <td>{i + 1}</td>
                <td>
                  <span className="tag">{c.source}</span> {c.title}
                </td>
                <td>{c.denseRank ?? "–"}</td>
                <td>{c.bm25Rank ?? "–"}</td>
                <td>{c.rrf.toFixed(4)}</td>
                <td>{c.rerankScore ?? "–"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="hint">Dòng tô đậm = đoạn được đưa vào ngữ cảnh cho LLM.</p>
    </details>
  );
}
