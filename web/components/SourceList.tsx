import type { SourceRef } from "@/lib/rag/types";

export default function SourceList({ sources }: { sources: SourceRef[] }) {
  return (
    <details className="sources" open>
      <summary>Nguồn tham khảo ({sources.length})</summary>
      <ol>
        {sources.map((s, i) => {
          // nhiều đoạn của cùng 1 bài -> đánh số "đoạn 1, đoạn 2" để phân biệt
          const same = sources.filter((x) => x.url === s.url && x.title === s.title);
          const part = same.length > 1 ? ` · đoạn ${sources.slice(0, i + 1).filter((x) => same.includes(x)).length}` : "";
          return (
          <li key={s.n} id={`cite-${s.n}`}>
            <span className="num">{s.n}</span>
            <div>
              {s.url ? (
                <a href={s.url} target="_blank" rel="noreferrer">
                  {s.title}
                  {part}
                </a>
              ) : (
                <strong>
                  {s.title}
                  {part}
                </strong>
              )}
              <div className="meta">
                {s.sourceName} · {s.category}
              </div>
              <p className="snippet">{s.snippet}…</p>
            </div>
          </li>
          );
        })}
      </ol>
    </details>
  );
}
