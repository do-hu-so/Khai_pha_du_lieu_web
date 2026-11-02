/**
 * Viết lại câu hỏi hội thoại thành câu hỏi độc lập (query condensation).
 * Ví dụ: [hỏi "Tứ diệu đế là gì?"] -> "Đế thứ hai nói gì?"  =>  "Tập đế (đế thứ hai trong Tứ diệu đế) nói gì?"
 * Nhờ vậy bước truy hồi tìm đúng tài liệu cho các câu hỏi nối tiếp.
 */
import { RAG_CONFIG } from "../config";
import { chatComplete } from "../generation/groq";
import type { ChatMessage } from "../types";

const SYSTEM = `Nhiệm vụ: viết lại câu hỏi cuối cùng của người dùng thành MỘT câu hỏi tiếng Việt độc lập, đầy đủ ngữ cảnh,
dựa vào lịch sử hội thoại (thay đại từ "nó", "điều đó", "vị ấy"... bằng đối tượng cụ thể).
Nếu câu hỏi đã rõ ràng thì giữ nguyên. Chỉ trả về câu hỏi, không giải thích.`;

export async function rewriteQuery(history: ChatMessage[], question: string): Promise<string> {
  if (history.length === 0) return question;
  const convo = history
    .slice(-RAG_CONFIG.context.historyTurns)
    .map((m) => `${m.role === "user" ? "Người dùng" : "Trợ lý"}: ${m.content.slice(0, 600)}`)
    .join("\n");
  try {
    const out = await chatComplete(
      [
        { role: "system", content: SYSTEM },
        { role: "user", content: `Lịch sử:\n${convo}\n\nCâu hỏi cuối: ${question}\n\nCâu hỏi độc lập:` },
      ],
      { model: RAG_CONFIG.groq.fastModel, temperature: 0, maxTokens: 150 },
    );
    const q = out.trim().replace(/^["“]|["”]$/g, "");
    return q.length > 3 && q.length < 500 ? q : question;
  } catch (e) {
    console.error("[rewrite] lỗi, dùng câu hỏi gốc:", e);
    return question;
  }
}
