# EN-04 · Pipeline xử lý tài liệu

| Thuộc tính | Giá trị |
|---|---|
| Loại | Enabler · EN. Enabler kỹ thuật |
| Sprint | Sprint 1 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | Enabler (bắt buộc cho các story phụ thuộc) |
| Story point | 8 `[Đề xuất]` |
| Vai trò thực hiện | AI engineer, Backend |
| Phụ thuộc | EN-02, EN-03 |
| Chặn bởi | — |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

Worker + hàng đợi trong PostgreSQL; trích xuất theo trang; phát hiện mật khẩu / hỏng / không có chữ; chia đoạn (ALG-1); thử lại 3 lần

**Truy vết:** ADR-05, ALG-1, SAD §2.2

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** Những gì không được liệt kê ở mục 4 và mục 6.

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

**Bảng CSDL** (trích migration `0001_init`, dev_tasks.md §0.3)

```sql
CREATE INDEX ix_doc_status ON documents.document (library_id, status);

CREATE INDEX ix_doc_name_trgm ON documents.document USING gin (file_name gin_trgm_ops);

CREATE TABLE documents.document_page (
  document_id uuid REFERENCES documents.document(id) ON DELETE CASCADE,
  page_number int NOT NULL,
  text text NOT NULL,
  PRIMARY KEY (document_id, page_number)
);

CREATE TABLE documents.text_chunk (
  id uuid PRIMARY KEY,
  document_id uuid NOT NULL REFERENCES documents.document(id) ON DELETE CASCADE,
  page_number int NOT NULL,
  chunk_index int NOT NULL,
  char_start int NOT NULL,
  char_end int NOT NULL,
  content text NOT NULL,
  tsv tsvector GENERATED ALWAYS AS (to_tsvector('simple', platform.f_unaccent(content))) STORED,
  embedding vector(1024) NOT NULL
);

CREATE INDEX ix_chunk_doc ON documents.text_chunk (document_id);

CREATE INDEX ix_chunk_tsv ON documents.text_chunk USING gin (tsv);

CREATE INDEX ix_chunk_vec ON documents.text_chunk USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

CREATE INDEX ix_job_ready ON platform.job (run_after) WHERE status = 'queued';
```

**Cấu hình**

| Biến | Mặc định |
|---|---|
| `EMBEDDER_URL`, `EMBED_DIM`, `EMBED_BATCH` | —, `1024`, `32` |
| `CHUNK_TOKENS`, `CHUNK_OVERLAP` | `500`, `80` |
| `NO_TEXT_CHARS_PER_PAGE` | `20` |

**Sự kiện phân tích** (danh sách cho phép, không có trường nội dung)

| name | Nguồn | props cho phép |
|---|---|---|
| `document_processing_completed` | worker | `page_count: int`, `duration_ms: int`, `status: ready \| no_text \| error` |

## 4. Công việc chi tiết

- [ ] **T-EN04.1** `BE` — **Job runner**: `adapters/jobs/runner.py`: `LISTEN jobs`, thêm vòng hỏi lại mỗi 5 s; lấy việc bằng `UPDATE platform.job SET status='running', locked_by=$1, locked_at=now(), attempts=attempts+1 WHERE id = (SELECT id FROM platform.job WHERE status='queued' AND run_after<=now() ORDER BY run_after FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING *`; chạy song song theo giới hạn từng loại job; khi khởi động thì trả các job `running` quá hạn (> timeout) về `queued`
- [ ] **T-EN04.2** `BE` — **Thử lại**: Lỗi → `status='queued'`, `run_after = now() + [30s, 2m, 10m][attempts-1]`; hết 3 lần → `failed` và `document.status='ERROR', error_code`
- [ ] **T-EN04.3** `BE` — **Trích xuất**: `adapters/pdf/pymupdf_extractor.py`: mở file; `needs_pass` → `PASSWORD`; ngoại lệ khi mở → `CORRUPT`; lấy text từng trang (`page.get_text("text")`), chuẩn hoá NFC
- [ ] **T-EN04.4** `BE` — **Phát hiện không có chữ**: Tổng ký tự (bỏ khoảng trắng) < `NO_TEXT_CHARS_PER_PAGE × page_count` → `NO_TEXT`, dừng
- [ ] **T-EN04.5** `BE` — **Bỏ header / footer lặp**: Dòng đầu / cuối trang xuất hiện trên ≥ 60% số trang → bỏ
- [ ] **T-EN04.6** `AI` — **Chia đoạn (ALG-1)**: `domain/documents/chunking.py`: cửa sổ `CHUNK_TOKENS` / `CHUNK_OVERLAP` **trong từng trang**, ưu tiên ngắt ở `\n\n` rồi đến dấu câu; tokenizer của BGE-M3 (hoặc ước lượng 1 token ≈ 4 ký tự nếu không có); giữ `char_start`, `char_end`
- [ ] **T-EN04.7** `BE` — **Ghi kết quả (idempotent)**: Trong 1 giao dịch: `DELETE text_chunk/document_page WHERE document_id=$1` → insert theo lô (`COPY` hoặc `executemany`) → `status='READY', page_count`; sự kiện `document_processing_completed`
- [ ] **T-EN04.8** `BE` — **Giới hạn tài nguyên**: Worker chạy bằng user không phải root, không có mạng ra ngoài (trừ embedder, storage, DB); timeout 10 phút / job; tối đa 2 job `process_document` song song

**Giả mã chia đoạn (ALG-1)** — `domain/documents/chunking.py`

```python
def chunk_page(page_no: int, text: str, size: int, overlap: int) -> list[Chunk]:
    chunks, start = [], 0
    while start < len(text):
        end = min(len(text), start + size * 4)              # ~4 ký tự / token
        if end < len(text):
            cut = max(text.rfind("\n\n", start, end), text.rfind(". ", start, end))
            if cut > start + size * 2:                       # chỉ cắt sớm nếu không làm đoạn quá ngắn
                end = cut + 1
        chunks.append(Chunk(page_no, start, end, text[start:end].strip()))
        if end == len(text):
            break
        start = max(end - overlap * 4, start + 1)
    return [c for c in chunks if c.content]
```

## 5. Trường hợp biên và lưu ý

- PDF có trang trống xen giữa → bỏ trang trống, vẫn giữ đúng `page_number` của trang khác.
- Worker bị khởi động lại giữa chừng → job `running` quá hạn được trả về `queued`; chạy lại không tạo dữ liệu trùng.

## 6. Tiêu chí nghiệm thu

- [ ] File 50 MB / 300 trang đạt "Sẵn sàng" ≤ 5 phút; chạy lại không tạo đoạn trùng (idempotent)

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| 300 trang, 50 MB → READY ≤ 5 phút (LG-07) | Integration (chạy ban đêm) | `big_300p.pdf` |
| File có mật khẩu → ERROR / PASSWORD | Integration | `locked.pdf` |
| File hỏng → ERROR / CORRUPT | Integration | `broken.pdf` |
| File scan → NO_TEXT | Integration | `scanned.pdf` |
| Chạy lại job 2 lần → số đoạn không đổi | Integration | `small_5p.pdf` |
| Không có đoạn nào vượt ranh giới trang; `char_start < char_end` | Unit | chuỗi tổng hợp |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.
- [ ] Test file 300 trang / 50 MB đạt ≤ 5 phút trên staging (LG-07).

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
