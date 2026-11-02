# Kho văn bản Phật giáo tiếng Việt · Khai phá văn bản · Chatbot RAG

Đề tài: **Xây dựng kho văn bản Phật giáo tiếng Việt và thực hiện một số tác vụ khai phá văn bản, XLNNTN cơ bản**,
sau đó xây dựng **chatbot hỏi đáp theo kiến trúc RAG** (Retrieval-Augmented Generation) chạy trên web,
deploy lên **Vercel**, mô hình ngôn ngữ dùng **Groq API**.

```
┌──────────────────────────── PYTHON (offline, chạy trên máy) ─────────────────────────────┐
│ 1.crawl ──► 2.preprocess ──► 3.mine (báo cáo)                                            │
│  data/raw/    data/processed/      reports/                                              │
│                    │                                                                     │
│                    └──► 4.chunk ──► 5.embed ──► data/index/ ──copy──► web/data/index/    │
└──────────────────────────────────────────────────────────────────────────────┬───────────┘
                                                                               │ (commit cùng repo)
┌──────────────────────────── WEB (Next.js trên Vercel) ───────────────────────▼───────────┐
│ câu hỏi ─► viết lại câu hỏi ─► embedding câu hỏi ─► Dense + BM25 ─► RRF ─► Rerank (LLM)   │
│         (Groq qwen3.8-27b)    (transformers.js)                     (Groq qwen3.8-27b)    │
│                                  ─► prompt + ngữ cảnh ─► Groq gpt-oss-120b ─► trả lời     │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

Kho văn bản được **embedding sẵn một lần** (Python) và lưu thành file trong project; web chỉ đọc
index này, không có bước upload/embedding tài liệu lúc chạy.

---

## 1. Cấu trúc thư mục

```
khai_pha_du_lieu_web/
├── config/                         # ⚙️ MỌI THAM SỐ ĐIỀU CHỈNH NẰM Ở ĐÂY
│   ├── sources.yaml                #   nguồn crawl: URL bắt đầu, regex bài viết, số bài tối đa...
│   ├── pipeline.yaml               #   tiền xử lý, chunking, mô hình embedding, khai phá
│   └── categories.yaml             #   luật gán nhãn chủ đề thống nhất
│
├── data/                           # 📦 TOÀN BỘ DỮ LIỆU
│   ├── raw/<nguồn>/documents.jsonl #   (1) dữ liệu thô sau khi crawl, mỗi nguồn 1 thư mục
│   ├── raw/manual/                 #       tài liệu bạn tự thêm (txt/md/html/pdf/docx)
│   ├── processed/corpus.jsonl      #   (2) KHO VĂN BẢN đã làm sạch, khử trùng, gán chủ đề
│   ├── processed/corpus_summary.json
│   ├── processed/doc_keywords.jsonl#       từ khóa TF-IDF từng văn bản (do bước mine sinh)
│   ├── chunks/chunks.jsonl         #   (4) các đoạn (chunk) cho RAG
│   ├── index/                      #   (5) VECTOR INDEX: manifest.json, chunks.json, embeddings.f32
│   └── eval/retrieval_questions.jsonl  # bộ câu hỏi đánh giá truy hồi
│
├── pipeline/                       # 🐍 MÃ NGUỒN PYTHON - mỗi bước 1 package
│   ├── __main__.py                 #   CLI: python -m pipeline <bước>
│   ├── config.py                   #   đường dẫn + đọc file cấu hình
│   ├── crawling/                   #   BƯỚC 1 - THU THẬP
│   │   ├── http.py                 #     HTTP lịch sự: robots.txt, giãn cách, retry
│   │   ├── html_crawler.py         #     focused crawler (danh mục -> bài viết), chạy tiếp được
│   │   ├── extract.py              #     trích nội dung chính (trafilatura) + breadcrumb
│   │   ├── vbeta_crawler.py        #     vbeta.vn qua API công khai (SPA Angular)
│   │   └── manual_import.py        #     nhập file thủ công
│   ├── preprocessing/              #   BƯỚC 2 - TIỀN XỬ LÝ & SẮP XẾP
│   │   ├── cleaner.py              #     Unicode NFC, chuẩn hóa dấu thanh, xóa boilerplate
│   │   ├── dedup.py                #     khử trùng lặp: fingerprint + MinHash/LSH
│   │   └── categorizer.py          #     gán chủ đề theo luật
│   ├── nlp/                        #   công cụ XLNNTN dùng chung
│   │   ├── normalize.py            #     chuẩn hóa tiếng Việt, token hóa BM25
│   │   ├── segmenter.py            #     tách từ (underthesea)
│   │   └── resources/vietnamese_stopwords.txt
│   ├── mining/                     #   BƯỚC 3 - KHAI PHÁ VĂN BẢN
│   │   ├── statistics.py           #     thống kê, phân bố, Zipf, n-gram
│   │   ├── keywords.py             #     từ khóa TF-IDF + word cloud
│   │   ├── topics.py               #     mô hình chủ đề LDA
│   │   ├── clustering.py           #     phân cụm K-Means + t-SNE
│   │   ├── classification.py       #     phân loại NB / LogReg / SVM
│   │   ├── ner.py                  #     nhận dạng thực thể
│   │   └── report.py               #     sinh reports/REPORT.md
│   ├── chunking/chunker.py         #   BƯỚC 4 - CHIA ĐOẠN (đoạn văn -> câu -> từ, có chồng lấp)
│   ├── embedding/                  #   BƯỚC 5 - EMBEDDING
│   │   ├── embedder.py             #     sentence-transformers (multilingual-e5-small)
│   │   └── build_index.py          #     ghi index + copy sang web/data/index
│   └── retrieval/                  #   thử truy hồi offline (cùng thuật toán với web)
│       ├── bm25.py, hybrid.py
│       ├── search.py               #     python -m pipeline search "câu hỏi"
│       └── evaluate.py             #     python -m pipeline evaluate  (Hit@k, MRR)
│
├── reports/                        # 📊 KẾT QUẢ KHAI PHÁ: REPORT.md, *.json, figures/*.png
│
└── web/                            # 🌐 CHATBOT (Next.js) - thư mục gốc khi deploy Vercel
    ├── data/index/                 #   bản copy của data/index (được đóng gói khi deploy)
    ├── lib/rag/                    #   ⭐ LÕI RAG - mỗi bước 1 thư mục
    │   ├── config.ts               #     ⚙️ tham số RAG (top-k, trọng số RRF, reranker, model...)
    │   ├── types.ts
    │   ├── pipeline.ts             #     bộ điều phối: rewrite → embed → retrieve → rerank → generate
    │   ├── index/store.ts          #     nạp index vào bộ nhớ
    │   ├── text/normalize.ts       #     chuẩn hóa tiếng Việt (port của pipeline/nlp/normalize.py)
    │   ├── query/rewrite.ts        #     [1] viết lại câu hỏi nối tiếp thành câu độc lập
    │   ├── embedding/query-embedder.ts  # [2] embedding câu hỏi (transformers.js, ONNX)
    │   ├── retrieval/              #     [3] TRUY HỒI
    │   │   ├── dense.ts            #         cosine similarity trên vector
    │   │   ├── bm25.ts             #         BM25 âm tiết + bigram
    │   │   └── hybrid.ts           #         hợp nhất Reciprocal Rank Fusion
    │   ├── reranking/              #     [4] XẾP HẠNG LẠI
    │   │   ├── llm-reranker.ts     #         LLM chấm điểm liên quan 0-10
    │   │   ├── mmr.ts              #         Maximal Marginal Relevance (không tốn API)
    │   │   └── index.ts            #         chọn chiến lược + chọn ngữ cảnh
    │   └── generation/             #     [5] SINH CÂU TRẢ LỜI
    │       ├── prompt.ts           #         system prompt + định dạng ngữ cảnh có trích dẫn
    │       └── groq.ts             #         client Groq (stream)
    ├── app/api/chat/route.ts       #   POST /api/chat   - hỏi đáp (stream NDJSON)
    ├── app/api/search/route.ts     #   POST /api/search - chỉ truy hồi (để kiểm tra)
    ├── app/api/health/route.ts     #   GET  /api/health - thông tin index
    ├── components/                 #   giao diện chat, nguồn trích dẫn, bảng chi tiết truy hồi
    └── scripts/check-index.mjs     #   kiểm tra index + độ khớp embedding Python ↔ web
```

## 2. Nguồn dữ liệu

| Nguồn | Cách thu thập | Ghi chú |
|---|---|---|
| phatgiao.org.vn | crawler HTML (danh mục → bài `-dNNN.html`) | Cổng TTPG Việt Nam |
| langmai.org | crawler HTML, nhận diện bài qua class `<body>` của WordPress | kinh văn, từ điển, bài viết Làng Mai |
| daophatngaynay.com | crawler HTML | kinh điển, triết học, lịch sử |
| vbeta.vn | **API công khai** `api.phapbao.org` (web là SPA Angular nên HTML rỗng) | Kinh / Luật / Luận / Sách, mỗi chương = 1 văn bản |
| thuvienhoasen.org | ❌ không crawl được (Cloudflare challenge, HTTP 403) | lưu bài thủ công vào `data/raw/manual/thuvienhoasen/` |
| tuvien.com | ❌ **tắt** trong cấu hình | robots.txt khai báo `Content-Signal: ai-train=no` và chặn bot AI |

Crawler tôn trọng `robots.txt`, giãn cách 1 giây/request cho mỗi host và chạy tiếp được khi bị ngắt.
Dữ liệu chỉ dùng cho mục đích học tập/nghiên cứu, chatbot luôn trích dẫn link bài gốc.

## 3. Cài đặt

**Python ≥ 3.10** (khuyến nghị môi trường ảo riêng):

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/macOS: source .venv/bin/activate)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
pip install lxml_html_clean        # trafilatura cần khi dùng lxml >= 5.2
```

**Node.js ≥ 20** cho web:

```bash
cd web
npm install
copy .env.example .env.local       # rồi điền GROQ_API_KEY (lấy tại https://console.groq.com/keys)
```

## 4. Chạy pipeline dữ liệu (Python)

Chạy tại thư mục gốc dự án:

```bash
python -m pipeline crawl            # 1. thu thập          -> data/raw/
python -m pipeline preprocess       # 2. làm sạch, sắp xếp -> data/processed/corpus.jsonl
python -m pipeline mine             # 3. khai phá          -> reports/REPORT.md
python -m pipeline chunk            # 4. chia đoạn         -> data/chunks/chunks.jsonl
python -m pipeline embed            # 5. embedding         -> data/index/ + web/data/index/
# hoặc chạy tất cả:  python -m pipeline all
```

Tùy chọn hữu ích:

```bash
python -m pipeline crawl --only langmai vbeta --max-articles 200   # crawl thêm vài nguồn
python -m pipeline crawl --fresh                                   # xóa dữ liệu thô, crawl lại
python -m pipeline mine --tasks stats keywords topics              # chỉ chạy vài tác vụ
python -m pipeline search "Tứ diệu đế là gì?" --mode hybrid -k 5   # thử truy hồi không cần web
python -m pipeline evaluate                                        # so sánh BM25 / Dense / Hybrid
```

`evaluate` chạy bộ câu hỏi trong `data/eval/retrieval_questions.jsonl` (mỗi câu kèm chuỗi con của tiêu đề
văn bản đúng) và tính **Hit@1/3/5, MRR@10** cho từng phương pháp → `reports/retrieval_eval.json`.
Khi mở rộng kho, hãy bổ sung câu hỏi vào file này để theo dõi chất lượng truy hồi.

**Mở rộng kho văn bản:** tăng `max_articles` trong `config/sources.yaml`, thêm `start_urls`, hoặc thêm nguồn mới
(chỉ cần khai báo regex bài viết/danh mục — không phải viết code). Sau đó chạy lại các bước 1→5.

## 5. Các tác vụ khai phá văn bản & XLNNTN

`python -m pipeline mine` sinh báo cáo `reports/REPORT.md` (kèm biểu đồ trong `reports/figures/`):

| # | Tác vụ | Kỹ thuật |
|---|---|---|
| 1 | Thống kê kho văn bản | phân bố theo nguồn/chủ đề, độ dài, kích thước từ vựng, type/token ratio, định luật Zipf, từ ghép và cụm từ phổ biến |
| 2 | Trích xuất từ khóa | tách từ (underthesea) + bỏ từ dừng + TF-IDF; từ khóa từng văn bản và từng chủ đề; word cloud |
| 3 | Mô hình chủ đề | LDA (Latent Dirichlet Allocation), đối chiếu topic với nhãn chủ đề |
| 4 | Phân cụm văn bản | TF-IDF → LSA (TruncatedSVD) → K-Means, chọn k bằng Silhouette, đánh giá ARI/NMI, trực quan t-SNE |
| 5 | Phân loại văn bản | TF-IDF (unigram + bigram từ) + Naive Bayes / Logistic Regression / Linear SVM, CV 5-fold, macro-F1, ma trận nhầm lẫn; 2 bài toán: đoán **chủ đề** và đoán **nguồn** |
| 6 | Nhận dạng thực thể | underthesea NER: nhân vật (PER), địa danh (LOC), tổ chức (ORG) |

Tiền xử lý (bước 2) cũng là các tác vụ XLNNTN: chuẩn hóa Unicode NFC, thống nhất kiểu bỏ dấu thanh
(`hoà`→`hòa`, `thuỷ`→`thủy`), lọc ngôn ngữ, khử trùng lặp gần đúng bằng MinHash-LSH.

## 6. Kiến trúc RAG (thư mục `web/lib/rag/`)

| Bước | File | Mô tả |
|---|---|---|
| Chunking | `pipeline/chunking/chunker.py` | ~900 ký tự/chunk, chồng lấp ~150 ký tự, cắt theo đoạn văn → câu → từ |
| Embedding (offline) | `pipeline/embedding/` | `intfloat/multilingual-e5-small` (384 chiều), tiền tố `passage: `, chuẩn hóa L2 |
| [1] Viết lại câu hỏi | `query/rewrite.ts` | câu hỏi nối tiếp ("vị ấy là ai?") → câu hỏi độc lập, dùng model nhanh `qwen/qwen3.8-27b` |
| [2] Embedding câu hỏi | `embedding/query-embedder.ts` | cùng mô hình e5 (bản ONNX `Xenova/multilingual-e5-small`) chạy bằng transformers.js, tiền tố `query: ` |
| [3] Truy hồi | `retrieval/` | **Dense** (cosine, top 30) + **BM25** (âm tiết + bigram, top 30) → **RRF** → tối đa 2 chunk/văn bản → 20 ứng viên |
| [4] Xếp hạng lại | `reranking/` | `llm`: Groq chấm điểm liên quan 0–10, loại < 3 · `mmr`: đa dạng hóa · `none` |
| [5] Sinh câu trả lời | `generation/` | 6 chunk tốt nhất làm ngữ cảnh, prompt bắt buộc trích dẫn `[n]`, stream từ Groq `openai/gpt-oss-120b` |

Model Groq mặc định (đã kiểm tra có trên tài khoản, 11/2026): `openai/gpt-oss-120b` để sinh câu trả lời,
`qwen/qwen3.8-27b` để viết lại câu hỏi và rerank. `groq.ts` tự thêm tham số suy luận phù hợp
(`reasoning_effort`) cho từng họ model. Đổi model bằng biến `GROQ_MODEL` / `GROQ_FAST_MODEL`.

Mọi tham số nằm trong `web/lib/rag/config.ts` và ghi đè được bằng biến môi trường (`.env.example`).
Bật **"Chi tiết truy hồi"** trên giao diện để xem thứ hạng Dense/BM25/RRF/Rerank của từng ứng viên,
câu hỏi sau khi viết lại và thời gian từng bước.

Kiểm tra truy hồi không cần giao diện (lưu câu hỏi vào file UTF-8 để tránh lỗi font tiếng Việt —
trên Windows, curl gửi trực tiếp chữ có dấu từ dòng lệnh sẽ bị hỏng thành `T? di?u d?`):

```bash
# Tạo file query.json bằng VS Code (mặc định lưu UTF-8), nội dung:
#   {"query": "Tứ diệu đế là gì?", "reranker": "llm"}
curl -X POST http://localhost:3000/api/search -H "Content-Type: application/json" --data-binary @query.json
```

### Hạn mức Groq (gói miễn phí)

Mỗi model: **8.000 token/phút, 1.000 request/ngày** (hạn mức tính riêng từng model). Mỗi câu hỏi tốn khoảng
2.500 token cho bước sinh và 2.000 token cho bước rerank. Khi model chính vượt hạn mức (HTTP 429),
`generation/groq.ts` tự chờ ngắn rồi chuyển sang model dự phòng (`GROQ_FALLBACK_MODELS`,
mặc định `openai/gpt-oss-20b,qwen/qwen3.8-27b`), nên người dùng hầu như không thấy lỗi. Bảng "Chi tiết truy hồi"
cho biết model nào đã trả lời. Nếu nhiều người dùng cùng lúc, hãy nâng cấp gói Groq hoặc đặt `RERANKER=mmr`
(rerank không tốn API).

## 7. Chạy web ở máy

```bash
cd web
npm run check-index      # kiểm tra index + embedding web khớp embedding Python (cosine > 0.98)
npm run dev              # http://localhost:3000
```

Lần hỏi đầu tiên server tải mô hình ONNX (~118MB) vào `web/.cache/`, các lần sau dùng lại.

## 8. Deploy lên Vercel

1. Đẩy toàn bộ repo lên GitHub (**bao gồm `web/data/index/`** — đó là kho đã embedding).
2. Vercel → *Add New Project* → chọn repo → **Root Directory = `web`** (framework tự nhận Next.js).
3. *Environment Variables*: thêm `GROQ_API_KEY` (các biến khác tùy chọn, xem `web/.env.example`).
4. Deploy. Kiểm tra `https://<tên-app>.vercel.app/api/health`.

Ghi chú kỹ thuật:
- `next.config.mjs` đã cấu hình đóng gói `data/index/**` vào serverless function và loại binary
  onnxruntime của nền tảng khác để gói nhỏ hơn giới hạn 250MB.
- Trên Vercel, mô hình embedding câu hỏi được tải về `/tmp` ở lần gọi đầu của mỗi instance
  (cold start chậm hơn vài giây). Nếu việc này lỗi, hệ thống tự chuyển sang chỉ dùng BM25.
- Khi cập nhật kho: chạy lại pipeline → commit `web/data/index/` → Vercel tự deploy lại.

## 9. Khắc phục sự cố

| Hiện tượng | Cách xử lý |
|---|---|
| `ImportError: lxml.html.clean ...` | `pip install lxml_html_clean` |
| Web báo "Chưa có index" | chạy `python -m pipeline embed` (hoặc `python -m pipeline export`) |
| "Thiếu GROQ_API_KEY" | tạo `web/.env.local` từ `.env.example`, khởi động lại `npm run dev` |
| Groq báo model không tồn tại | đổi `GROQ_MODEL` / `GROQ_FAST_MODEL` theo https://console.groq.com/docs/models |
| "vượt hạn mức miễn phí của Groq" | đợi ~1 phút; hoặc thêm model vào `GROQ_FALLBACK_MODELS`; hoặc `RERANKER=mmr` |
| Test bằng curl ra kết quả vô nghĩa | lỗi mã hóa tiếng Việt trên Windows — gửi body từ file UTF-8 (`--data-binary @file.json`) |
| Crawler lấy ít bài / sai trang | sửa `article_url_regex`, `follow_url_regex` trong `config/sources.yaml` |
