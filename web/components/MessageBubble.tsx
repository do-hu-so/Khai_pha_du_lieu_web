"use client";

import ReactMarkdown from "react-markdown";
import SourceList from "./SourceList";
import TraceTable from "./TraceTable";
import type { UIMessage } from "./types";

/** Biến "[2]" trong câu trả lời thành liên kết tới nguồn tương ứng. */
function linkCitations(text: string, count: number): string {
  return text.replace(/\[(\d{1,2})\](?!\()/g, (m, n) => (+n >= 1 && +n <= count ? `[\\[${n}\\]](#cite-${n})` : m));
}

export default function MessageBubble({ message, showTrace }: { message: UIMessage; showTrace: boolean }) {
  if (message.role === "user") {
    return (
      <div className="msg user">
        <div className="bubble">{message.content}</div>
      </div>
    );
  }
  const sources = message.sources ?? [];
  return (
    <div className="msg assistant">
      <div className="bubble">
        {message.pending && !message.content ? (
          <p className="thinking">
            {message.sources ? "Đang soạn câu trả lời" : "Đang tìm trong kho văn bản"}
            <span className="dots" aria-hidden>
              <i />
              <i />
              <i />
            </span>
          </p>
        ) : (
          <div className="markdown">
            <ReactMarkdown
              components={{
                a: ({ href, children }) => {
                  const n = href?.startsWith("#cite-") ? Number(href.slice(6)) : 0;
                  const src = n ? sources[n - 1] : undefined;
                  return src ? (
                    <a className="cite" href={src.url} target="_blank" rel="noreferrer" title={`${src.title} — ${src.sourceName}`}>
                      {n}
                    </a>
                  ) : (
                    <a href={href} target="_blank" rel="noreferrer">
                      {children}
                    </a>
                  );
                },
              }}
            >
              {linkCitations(message.content, sources.length)}
            </ReactMarkdown>
          </div>
        )}
        {message.error && <p className="error">Lỗi: {message.error}</p>}
        {sources.length > 0 && !message.pending && <SourceList sources={sources} />}
        {showTrace && message.trace && <TraceTable trace={message.trace} />}
      </div>
    </div>
  );
}
