# EN-05 · Truy xuất lai (ChunkIndex)

| Thuộc tính | Giá trị |
|---|---|
| Loại | Enabler · EN. Enabler kỹ thuật |
| Sprint | Sprint 2 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | Enabler (bắt buộc cho các story phụ thuộc) |
| Story point | 8 `[Đề xuất]` |
| Vai trò thực hiện | AI engineer, Backend, QA |
| Phụ thuộc | EN-04 |
| Chặn bởi | — |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

Vector HNSW + FTS + RRF, top 8, ≤ 3 đoạn / tài liệu; ngưỡng `τ` trong cấu hình

**Truy vết:** ADR-07, ALG-2

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** Những gì không được liệt kê ở mục 4 và mục 6.

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

**Bảng CSDL** (trích migration `0001_init`, dev_tasks.md §0.3)

```sql
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
```

**Cấu hình**

| Biến | Mặc định |
|---|---|
| `RETR_TOPK_VECTOR`, `RETR_TOPK_FTS`, `RETR_TOPN`, `RETR_MAX_PER_DOC`, `RETR_TAU`, `RRF_K`, `HNSW_EF_SEARCH` | `30`, `30`, `8`, `3`, `0.35`, `60`, `80` |

## 4. Công việc chi tiết

- [ ] **T-EN05.1** `BE` — **Port**: `ports/chunk_index.py`: `upsert(document_id, chunks)`, `search(query: str, query_vec: list[float], doc_ids: list[UUID]) -> SearchResult(chunks: list[ScoredChunk], max_cosine: float, fts_hits: int)`
- [ ] **T-EN05.2** `AI` — **Truy vấn vector**: `SET LOCAL hnsw.ef_search = :ef; SELECT id, document_id, page_number, content, 1 - (embedding <=> :q) AS cos FROM documents.text_chunk WHERE document_id = ANY(:docs) ORDER BY embedding <=> :q LIMIT :k`
- [ ] **T-EN05.3** `AI` — **Truy vấn toàn văn**: `SELECT id, …, ts_rank_cd(tsv, q) AS r FROM documents.text_chunk, websearch_to_tsquery('simple', platform.f_unaccent(:text)) q WHERE document_id = ANY(:docs) AND tsv @@ q ORDER BY r DESC LIMIT :k`
- [ ] **T-EN05.4** `AI` — **RRF + lọc**: Chạy 2 truy vấn song song (`asyncio.gather`, 2 kết nối); `score = Σ 1/(RRF_K + rank)`; sắp xếp; tối đa `RETR_MAX_PER_DOC` mỗi tài liệu; lấy `RETR_TOPN`
- [ ] **T-EN05.5** `AI` — **Quyết định "không có đoạn"**: `if max_cosine < RETR_TAU and fts_hits == 0 → NO_CHUNKS` (ALG-2)
- [ ] **T-EN05.6** `AI` — **Cache embedding câu hỏi**: LRU 1.000 mục trong tiến trình, khoá = chuỗi câu hỏi đã chuẩn hoá NFC + lowercase
- [ ] **T-EN05.7** `QA` — **Test hiệu năng truy xuất**: Nạp 300.000 đoạn giả (vector ngẫu nhiên đã chuẩn hoá) → p95 ≤ 250 ms

**Lưu ý:** `doc_ids` luôn lấy từ `DocumentLibrary.readyDocuments()` (`status='READY' AND removed_at IS NULL`). Không bao giờ truy vấn chỉ mục mà không lọc theo danh sách này (RUL-003).

## 5. Trường hợp biên và lưu ý

- Xem các trường hợp lỗi ở mục 3 (mã lỗi) và các tiêu chí nghiệm thu ở mục 6.

## 6. Tiêu chí nghiệm thu

- [ ] ≤ 250 ms p95 với 300.000 đoạn; chỉ trả đoạn của tài liệu READY chưa gỡ

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Kiểm chứng tiêu chí hoàn thành ở mục 6 | Integration / báo cáo | EN-05 |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
