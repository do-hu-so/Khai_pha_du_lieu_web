/**
 * POST /api/chat  - hỏi đáp RAG, trả về luồng NDJSON (mỗi dòng 1 sự kiện JSON):
 *   {"type":"meta","sources":[...],"trace":{...}}   nguồn trích dẫn + chi tiết truy hồi
 *   {"type":"delta","text":"..."}                   từng mẩu câu trả lời
 *   {"type":"error","message":"..."}
 *   {"type":"done"}
 * Body: { "messages": [{ "role": "user" | "assistant", "content": "..." }, ...] }
 */
import { chatStream } from "@/lib/rag/generation/groq";
import { prepareAnswer } from "@/lib/rag/pipeline";
import type { ChatMessage } from "@/lib/rag/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

export async function POST(req: Request) {
  let messages: ChatMessage[];
  try {
    ({ messages } = (await req.json()) as { messages: ChatMessage[] });
  } catch {
    return Response.json({ error: "Body không hợp lệ" }, { status: 400 });
  }
  const valid = Array.isArray(messages)
    ? messages.filter((m) => (m.role === "user" || m.role === "assistant") && typeof m.content === "string")
    : [];
  const last = valid.at(-1);
  if (!last || last.role !== "user" || !last.content.trim()) {
    return Response.json({ error: "Thiếu câu hỏi" }, { status: 400 });
  }
  const question = last.content.trim().slice(0, 1000);
  const history = valid.slice(0, -1);

  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      let closed = false;
      const send = (obj: unknown) => {
        if (closed) return;
        try {
          controller.enqueue(encoder.encode(JSON.stringify(obj) + "\n"));
        } catch {
          closed = true; // client đã ngắt kết nối (bấm "Dừng")
        }
      };
      try {
        const t0 = Date.now();
        const { sources, trace, llmMessages } = await prepareAnswer(question, history);
        send({ type: "meta", sources, trace });
        let model = "";
        for await (const text of chatStream(llmMessages, { signal: req.signal, onModel: (m) => (model = m) })) {
          send({ type: "delta", text });
        }
        trace.timingsMs.total = Date.now() - t0;
        send({ type: "done", timingsMs: trace.timingsMs, model });
      } catch (e) {
        if (!req.signal.aborted) console.error("[chat]", e);
        send({ type: "error", message: e instanceof Error ? e.message : String(e) });
      } finally {
        if (!closed) {
          closed = true;
          try {
            controller.close();
          } catch {
            /* đã đóng */
          }
        }
      }
    },
    cancel() {
      /* client hủy - req.signal sẽ dừng lời gọi Groq */
    },
  });

  return new Response(stream, {
    headers: { "Content-Type": "application/x-ndjson; charset=utf-8", "Cache-Control": "no-store" },
  });
}
