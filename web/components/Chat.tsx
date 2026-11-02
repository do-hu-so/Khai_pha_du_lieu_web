"use client";

import { useEffect, useRef, useState } from "react";
import MessageBubble from "./MessageBubble";
import type { HealthInfo, UIMessage } from "./types";

const SUGGESTIONS = [
  "Tứ diệu đế là gì?",
  "Bát chánh đạo gồm những yếu tố nào?",
  "Thực tập chánh niệm trong đời sống hằng ngày như thế nào?",
  "Ý nghĩa của Bát Nhã Tâm Kinh?",
  "Ngũ giới của người Phật tử là gì?",
];

const uid = () => Math.random().toString(36).slice(2, 10);

export default function Chat() {
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [showTrace, setShowTrace] = useState(false);
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ ok: false, error: "Không kết nối được máy chủ" }));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const patchLast = (fn: (m: UIMessage) => UIMessage) =>
    setMessages((ms) => ms.map((m, i) => (i === ms.length - 1 ? fn(m) : m)));

  async function send(text: string) {
    const question = text.trim();
    if (!question || busy) return;
    const history = messages
      .filter((m) => !m.error && m.content)
      .map(({ role, content }) => ({ role, content }));
    setMessages((ms) => [
      ...ms,
      { id: uid(), role: "user", content: question },
      { id: uid(), role: "assistant", content: "", pending: true },
    ]);
    setInput("");
    setBusy(true);
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: [...history, { role: "user", content: question }] }),
        signal: ctrl.signal,
      });
      if (!res.ok || !res.body) throw new Error((await res.json().catch(() => null))?.error ?? `HTTP ${res.status}`);
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        let nl: number;
        while ((nl = buf.indexOf("\n")) >= 0) {
          const line = buf.slice(0, nl);
          buf = buf.slice(nl + 1);
          if (!line.trim()) continue;
          const ev = JSON.parse(line);
          if (ev.type === "meta") patchLast((m) => ({ ...m, sources: ev.sources, trace: ev.trace }));
          else if (ev.type === "delta") patchLast((m) => ({ ...m, content: m.content + ev.text, pending: false }));
          else if (ev.type === "error") patchLast((m) => ({ ...m, error: ev.message, pending: false }));
          else if (ev.type === "done")
            patchLast((m) => ({
              ...m,
              pending: false,
              trace: m.trace
                ? { ...m.trace, timingsMs: ev.timingsMs ?? m.trace.timingsMs, generationModel: ev.model }
                : m.trace,
            }));
        }
      }
    } catch (e) {
      if ((e as Error).name !== "AbortError") patchLast((m) => ({ ...m, error: (e as Error).message }));
    } finally {
      patchLast((m) => ({ ...m, pending: false }));
      setBusy(false);
      abortRef.current = null;
    }
  }

  const idx = health?.index;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo" aria-hidden>☸</span>
          <div>
            <h1>Hỏi đáp Phật học</h1>
            <p>Trả lời dựa trên kho văn bản Phật giáo tiếng Việt, có trích dẫn nguồn</p>
          </div>
        </div>
        <div className="actions">
          <label className="toggle">
            <input type="checkbox" checked={showTrace} onChange={(e) => setShowTrace(e.target.checked)} />
            Chi tiết truy hồi
          </label>
          <button className="ghost" onClick={() => setMessages([])} disabled={busy || messages.length === 0}>
            Cuộc trò chuyện mới
          </button>
        </div>
      </header>

      <main className="thread">
        {messages.length === 0 ? (
          <section className="welcome">
            <h2>Bạn muốn tìm hiểu điều gì?</h2>
            <p>
              Câu trả lời được tổng hợp từ các bài viết, kinh sách trên những trang Phật giáo uy tín.
              Mỗi ý đều kèm số trích dẫn để bạn đối chiếu với bản gốc.
            </p>
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => send(s)} disabled={busy}>
                  {s}
                </button>
              ))}
            </div>
          </section>
        ) : (
          messages.map((m) => <MessageBubble key={m.id} message={m} showTrace={showTrace} />)
        )}
        <div ref={bottomRef} />
      </main>

      <footer className="composer">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                send(input);
              }
            }}
            placeholder="Nhập câu hỏi về Phật pháp… (Enter để gửi, Shift+Enter xuống dòng)"
            rows={1}
            maxLength={1000}
            aria-label="Câu hỏi"
          />
          {busy ? (
            <button type="button" className="primary" onClick={() => abortRef.current?.abort()}>
              Dừng
            </button>
          ) : (
            <button type="submit" className="primary" disabled={!input.trim()}>
              Gửi
            </button>
          )}
        </form>
        <p className="status">
          {health === null
            ? "Đang kiểm tra kho dữ liệu…"
            : health.ok && idx
              ? `Kho: ${idx.numDocs.toLocaleString("vi-VN")} văn bản · ${idx.numChunks.toLocaleString("vi-VN")} đoạn · ${Object.keys(idx.sources).length} nguồn` +
                (health.config?.groqConfigured ? "" : " · ⚠ chưa cấu hình GROQ_API_KEY")
              : `⚠ ${health.error ?? "Chưa có index"} - hãy chạy "python -m pipeline embed"`}
        </p>
      </footer>
    </div>
  );
}
