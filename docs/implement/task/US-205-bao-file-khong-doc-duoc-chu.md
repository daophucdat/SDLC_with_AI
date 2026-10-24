# US-205 · Báo file không đọc được chữ

| Thuộc tính | Giá trị |
|---|---|
| Loại | User story · E2. Kho tài liệu |
| Sprint | Sprint 3 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | P1 |
| Story point | 2 `[Đề xuất]` |
| Vai trò thực hiện | Backend, Frontend, QA |
| Phụ thuộc | EN-04 |
| Chặn bởi | — |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

> Là **chuyên viên BD**, tôi muốn được báo khi PDF không có chữ đọc được (file scan), để không tưởng rằng file đó đã được tra cứu.

**Truy vết:** BR-006 · UCD-07 · EC-10 · ASM-003

**Thiết kế giao diện:** [`workspace.html (Scan_hop_dong_2019.pdf)`](../../04-design/UI_UX_design/workspace.html)

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** Những gì không được liệt kê ở mục 4 và mục 6.

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

**Bảng CSDL** (trích migration `0001_init`, dev_tasks.md §0.3)

```sql
CREATE INDEX ix_doc_status ON documents.document (library_id, status);

CREATE INDEX ix_doc_name_trgm ON documents.document USING gin (file_name gin_trgm_ops);

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
| `NO_TEXT_CHARS_PER_PAGE` | `20` |

## 4. Công việc chi tiết

- [ ] **T205.1** `BE` — **Đã có ở T-EN04.4**: Đảm bảo `NO_TEXT` không bao giờ có dòng `text_chunk`
- [ ] **T205.2** `FE` — **Hiển thị**: Badge cảnh báo "Không đọc được chữ" + "File dạng ảnh scan, không được dùng để trả lời"; toast khi chuyển sang trạng thái này
- [ ] **T205.3** `QA` — **Bộ 10 file scan**: `backend/tests/fixtures/pdf/scanned_*.pdf` → 10/10 NO_TEXT (AC-006)

## 5. Trường hợp biên và lưu ý

- Xem các trường hợp lỗi ở mục 3 (mã lỗi) và các tiêu chí nghiệm thu ở mục 6.

## 6. Tiêu chí nghiệm thu

- [ ] **AC-205.1** — *Given* bộ 10 file PDF dạng ảnh scan, *When* tải lên, *Then* 10/10 có trạng thái "Không đọc được chữ" kèm giải thích (AC-006).
- [ ] **AC-205.2** — *Given* một file "Không đọc được chữ", *When* tôi đặt câu hỏi, *Then* file đó không xuất hiện trong trích dẫn.

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Kiểm chứng AC-205.1 như mô tả ở mục 6 | Integration | AC-205.1 |
| Kiểm chứng AC-205.2 như mô tả ở mục 6 | Integration | AC-205.2 |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
