# US-308 · Xem lại hội thoại hiện tại

| Thuộc tính | Giá trị |
|---|---|
| Loại | User story · E3. Hỏi đáp có dẫn nguồn |
| Sprint | Sprint 4 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | P2 |
| Story point | 3 `[Đề xuất]` |
| Vai trò thực hiện | Backend, Frontend |
| Phụ thuộc | — |
| Chặn bởi | PQ-003 (có lưu lịch sử qua phiên không) |
| Feature flag | `history` |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

> Là **chuyên viên BD**, tôi muốn xem lại các câu hỏi và câu trả lời trong cuộc hội thoại hiện tại, để không phải hỏi lại.

**Truy vết:** BR-010 · UCD-18 · PD-04

**Thiết kế giao diện:** [`workspace.html`](../../04-design/UI_UX_design/workspace.html)

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** Lưu hội thoại qua nhiều phiên (PD-04, PQ-003).

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

**API**

| # | Endpoint | Request | Response 2xx | Lỗi (code) | Story |
|---|---|---|---|---|---|
| Q3 | `GET /api/v1/conversations/{id}/questions` | — | `TurnDto[]` | 404 | US-308 |

**Bảng CSDL** (trích migration `0001_init`, dev_tasks.md §0.3)

```sql
CREATE TABLE qa.question (
  id uuid PRIMARY KEY,
  conversation_id uuid NOT NULL REFERENCES qa.conversation(id) ON DELETE CASCADE,
  text text NOT NULL CHECK (char_length(text) BETWEEN 1 AND 2000),
  language text NOT NULL CHECK (language IN ('vi','en')),
  is_followup boolean NOT NULL DEFAULT false,
  asked_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX ix_question_conv ON qa.question (conversation_id, asked_at);

CREATE TABLE qa.answer (
  id uuid PRIMARY KEY,
  question_id uuid NOT NULL UNIQUE REFERENCES qa.question(id) ON DELETE CASCADE,
  text text NOT NULL DEFAULT '',
  status text NOT NULL CHECK (status IN ('STREAMING','COMPLETED','NOT_FOUND','STOPPED','FAILED')),
  not_found_reason text,                     -- NO_CHUNKS | MODEL_NOT_FOUND | INVALID_CITATIONS
  latency_ms int,
  first_token_ms int,
  model_id text,
  completed_at timestamptz
);

CREATE TABLE qa.citation (
  answer_id uuid REFERENCES qa.answer(id) ON DELETE CASCADE,
  idx int NOT NULL,
  chunk_id uuid REFERENCES documents.text_chunk(id) ON DELETE SET NULL,    -- EC-15
  document_id uuid NOT NULL,
  file_name text NOT NULL,
  page_number int NOT NULL,
  excerpt text NOT NULL,
  PRIMARY KEY (answer_id, idx)
);
```

## 4. Công việc chi tiết

- [ ] `BE` `GET /conversations/{id}/questions` (chỉ chủ phiên).
- [ ] `FE` khi tải lại trang, khôi phục `turns` từ API; virtualize danh sách khi > 50 lượt

## 5. Trường hợp biên và lưu ý

- Xem các trường hợp lỗi ở mục 3 (mã lỗi) và các tiêu chí nghiệm thu ở mục 6.

## 6. Tiêu chí nghiệm thu

- [ ] **AC-308.1** — *Given* tôi đã hỏi 10 lượt trong phiên, *When* tôi cuộn lại hoặc tải lại trang, *Then* cả 10 cặp câu hỏi và câu trả lời đều xem lại được (AC-010).
- [ ] **AC-308.2** — *Given* tôi đăng xuất rồi đăng nhập lại, *When* mở màn hình làm việc, *Then* hội thoại cũ không còn (PD-04).

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Kiểm chứng AC-308.1 như mô tả ở mục 6 | Integration | AC-308.1 |
| Kiểm chứng AC-308.2 như mô tả ở mục 6 | Integration | AC-308.2 |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
