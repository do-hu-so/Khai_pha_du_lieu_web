/**
 * Client tối giản cho Groq (API tương thích OpenAI) - dùng fetch, không cần SDK.
 *
 * Gói miễn phí của Groq giới hạn MỖI MODEL ~8.000 token/phút và 1.000 request/ngày.
 * Khi gặp lỗi 429 (vượt hạn mức) / 5xx: chờ ngắn rồi thử lại, sau đó chuyển sang model dự phòng
 * (mỗi model có hạn mức riêng) -> người dùng hầu như không thấy lỗi.
 */
import { RAG_CONFIG } from "../config";

export interface LlmMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

interface ChatOptions {
  model?: string;
  temperature?: number;
  maxTokens?: number;
  json?: boolean;
  signal?: AbortSignal;
  /** gọi lại khi biết model thực sự trả lời (có thể là model dự phòng) */
  onModel?: (model: string) => void;
}

export class GroqError extends Error {
  constructor(public status: number, detail: string) {
    super(
      status === 429
        ? "Hệ thống đang vượt hạn mức miễn phí của Groq (token/phút). Vui lòng thử lại sau ít giây."
        : `Groq API lỗi ${status}: ${detail.slice(0, 300)}`,
    );
  }
}

/**
 * Tham số riêng cho các model có suy luận (reasoning) trên Groq:
 *  - openai/gpt-oss-*: suy luận ít ("low") cho nhanh, không trả phần suy luận về
 *  - qwen/qwen3*     : tắt suy luận (nhanh nhất, phù hợp viết lại câu hỏi / chấm điểm)
 */
function reasoningParams(model: string): Record<string, unknown> {
  if (model.startsWith("openai/gpt-oss")) return { reasoning_effort: "low", include_reasoning: false };
  if (model.startsWith("qwen/qwen3")) return { reasoning_effort: "none" };
  return {};
}

function body(model: string, messages: LlmMessage[], o: ChatOptions, stream: boolean) {
  return JSON.stringify({
    model,
    messages,
    temperature: o.temperature ?? RAG_CONFIG.groq.temperature,
    max_completion_tokens: o.maxTokens ?? RAG_CONFIG.groq.maxTokens,
    stream,
    ...reasoningParams(model),
    ...(o.json ? { response_format: { type: "json_object" } } : {}),
  });
}

/** Thời gian chờ Groq gợi ý (header retry-after hoặc "try again in 1.77s" trong thông báo lỗi). */
function retryAfterMs(res: Response, text: string): number {
  const header = Number(res.headers.get("retry-after"));
  if (header > 0) return header * 1000;
  const m = text.match(/try again in (?:(\d+)m)?([\d.]+)(ms|s)/i);
  if (!m) return 2000;
  return (Number(m[1] ?? 0) * 60 + Number(m[2]) / (m[3] === "ms" ? 1000 : 1)) * 1000;
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const RETRYABLE = new Set([429, 500, 502, 503]);

/** Gửi request, tự thử lại / chuyển model dự phòng. Trả về Response thành công đầu tiên. */
async function request(messages: LlmMessage[], o: ChatOptions, stream: boolean): Promise<Response> {
  if (!RAG_CONFIG.groq.apiKey) throw new Error("Thiếu GROQ_API_KEY (khai báo trong web/.env.local hoặc Vercel).");
  const primary = o.model ?? RAG_CONFIG.groq.model;
  const models = [primary, ...RAG_CONFIG.groq.fallbackModels.filter((m) => m !== primary)];
  let lastError: GroqError | null = null;

  for (const model of models) {
    for (let attempt = 0; attempt < 2; attempt++) {
      const res = await fetch(`${RAG_CONFIG.groq.baseUrl}/chat/completions`, {
        method: "POST",
        headers: { Authorization: `Bearer ${RAG_CONFIG.groq.apiKey}`, "Content-Type": "application/json" },
        body: body(model, messages, o, stream),
        signal: o.signal,
      });
      if (res.ok) {
        if (model !== primary) console.warn(`[groq] ${primary} quá tải -> dùng model dự phòng ${model}`);
        o.onModel?.(model);
        return res;
      }
      const text = await res.text();
      lastError = new GroqError(res.status, text);
      if (!RETRYABLE.has(res.status)) throw lastError;
      const wait = retryAfterMs(res, text);
      // chờ ngắn thì thử lại cùng model; chờ lâu thì chuyển ngay sang model dự phòng
      if (attempt === 0 && wait <= 3000) {
        await sleep(wait + 250);
        continue;
      }
      break;
    }
  }
  throw lastError!;
}

/** Gọi không stream, trả về nội dung text. */
export async function chatComplete(messages: LlmMessage[], o: ChatOptions = {}): Promise<string> {
  const res = await request(messages, o, false);
  const data = await res.json();
  return data.choices?.[0]?.message?.content ?? "";
}

/** Gọi có stream (Server-Sent Events), trả về từng mẩu text. */
export async function* chatStream(messages: LlmMessage[], o: ChatOptions = {}): AsyncGenerator<string> {
  const res = await request(messages, o, true);
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let nl: number;
    while ((nl = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, nl).trim();
      buf = buf.slice(nl + 1);
      if (!line.startsWith("data:")) continue;
      const payload = line.slice(5).trim();
      if (payload === "[DONE]") return;
      try {
        const delta = JSON.parse(payload).choices?.[0]?.delta?.content;
        if (delta) yield delta as string;
      } catch {
        /* dòng không hoàn chỉnh - bỏ qua */
      }
    }
  }
}
