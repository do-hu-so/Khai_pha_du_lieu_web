# Tài liệu nhập thủ công

Đặt tài liệu vào thư mục này để đưa vào kho văn bản (không cần crawl):

- Định dạng hỗ trợ: `.txt`, `.md`, `.html`/`.htm`, `.pdf` (cần `pypdf`), `.docx` (cần `python-docx`)
- Thư mục con cấp 1 được dùng làm **tên nguồn**, ví dụ:
  ```
  manual/
  ├── thuvienhoasen/            # trang bị Cloudflare chặn crawl -> lưu bài thủ công (Ctrl+S)
  │   ├── tu-dieu-de.html
  │   └── tu-dieu-de.meta.json  # (tùy chọn) {"title": "...", "url": "https://...", "author": "...", "category": "..."}
  └── sach-cua-toi.pdf          # file đặt trực tiếp -> nguồn "manual"
  ```
- File `<tên>.meta.json` (tùy chọn) khai báo tiêu đề, URL gốc (để chatbot trích dẫn), tác giả, chuyên mục.

Sau khi thêm tài liệu, chạy lại:

```bash
python -m pipeline crawl --only manual
python -m pipeline preprocess
python -m pipeline chunk
python -m pipeline embed
```
