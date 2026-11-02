/**
 * Xây dựng prompt cho bước sinh câu trả lời (Generation) từ ngữ cảnh đã truy hồi.
 */
import type { Candidate, ChatMessage } from "../types";
import type { LlmMessage } from "./groq";

export const SYSTEM_PROMPT = `Bạn là trợ lý hỏi đáp về Phật giáo, trả lời bằng tiếng Việt, giọng văn từ hòa, rõ ràng, chính xác.

NGUYÊN TẮC:
1. CHỈ dựa vào các TÀI LIỆU THAM KHẢO được cung cấp. Không bịa đặt kinh văn, tên người, số liệu.
2. Trích dẫn nguồn ngay sau ý sử dụng bằng số trong ngoặc vuông, ví dụ: "... gồm Khổ, Tập, Diệt, Đạo [1][3]."
3. Nếu tài liệu không đủ để trả lời, hãy nói rõ "Các tài liệu hiện có chưa đề cập đầy đủ đến vấn đề này" và
   chỉ nêu những gì tài liệu có. Có thể gợi ý người hỏi tìm hiểu thêm.
4. Giữ nguyên thuật ngữ Phật học (Hán-Việt, Pāli) như trong tài liệu; có thể giải thích ngắn gọn.
   Viết hoàn toàn bằng tiếng Việt, không chèn từ tiếng Anh.
5. Trình bày mạch lạc bằng Markdown (đoạn văn, gạch đầu dòng khi liệt kê). Không lặp lại câu hỏi.
6. Với câu hỏi không liên quan đến Phật giáo hoặc nội dung tài liệu, lịch sự từ chối và hướng người dùng về chủ đề Phật học.`;

export function formatContext(selected: Candidate[]): string {
  return selected
    .map((c, i) => `[${i + 1}] ${c.chunk.title}\nNguồn: ${c.chunk.source_name}\n${c.chunk.text}`)
    .join("\n\n---\n\n");
}

export function buildMessages(history: ChatMessage[], question: string, selected: Candidate[]): LlmMessage[] {
  const ctx = selected.length ? formatContext(selected) : "(Không tìm thấy tài liệu liên quan)";
  return [
    { role: "system", content: SYSTEM_PROMPT },
    ...history.slice(-4).map((m) => ({ role: m.role, content: m.content.slice(0, 1500) }) as LlmMessage),
    {
      role: "user",
      content: `TÀI LIỆU THAM KHẢO:\n\n${ctx}\n\n=====\nCÂU HỎI: ${question}\n\nHãy trả lời dựa trên tài liệu tham khảo ở trên, có trích dẫn [số].`,
    },
  ];
}
