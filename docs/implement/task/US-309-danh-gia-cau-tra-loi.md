# US-309 · Đánh giá câu trả lời

| Thuộc tính | Giá trị |
|---|---|
| Loại | User story · E3. Hỏi đáp có dẫn nguồn |
| Sprint | Sprint 3 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | P1 |
| Story point | 3 `[Đề xuất]` |
| Vai trò thực hiện | Backend, Frontend |
| Phụ thuộc | EN-08 (sự kiện) |
| Chặn bởi | — |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

> Là **trưởng nhóm BD**, tôi muốn thành viên đánh giá hữu ích / chưa tốt cho từng câu trả lời, để phát hiện sớm loại câu hỏi sản phẩm trả lời kém.

**Truy vết:** PD-03 · KR3.2 · UCD-25

**Thiết kế giao diện:** [`workspace.html?demo=answer`](../../04-design/UI_UX_design/workspace.html?demo=answer)

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** Những gì không được liệt kê ở mục 4 và mục 6.

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

**API**

| # | Endpoint | Request | Response 2xx | Lỗi (code) | Story |
|---|---|---|---|---|---|
| Q5 | `POST /api/v1/answers/{id}/feedback` | `{value, reason?}` | 204 | 400 · 409 ALREADY_SUBMITTED | US-309 |

**Bảng CSDL** (trích migration `0001_init`, dev_tasks.md §0.3)

```sql
CREATE TABLE qa.feedback (
  answer_id uuid PRIMARY KEY REFERENCES qa.answer(id) ON DELETE CASCADE,
  value text NOT NULL CHECK (value IN ('HELPFUL','NOT_HELPFUL')),
  reason text CHECK (reason IN ('wrong','incomplete','wrong_source','other')),
  submitted_at timestamptz NOT NULL DEFAULT now()
);
```

**Mã lỗi**

| code | HTTP | Thông điệp FE (`vi.ts`) | Hành động FE |
|---|---|---|---|
| INVALID_STATE | 409 | — | Làm mới dữ liệu |

**Sự kiện phân tích** (danh sách cho phép, không có trường nội dung)

| name | Nguồn | props cho phép |
|---|---|---|
| `answer_feedback_submitted` | BE | `value`, `reason` |

## 4. Công việc chi tiết

- [ ] **T309.1** `BE` — **`POST /answers/{id}/feedback`**: Chỉ cho `status=COMPLETED` và chủ hội thoại; `INSERT … ON CONFLICT DO NOTHING` → 409 nếu đã gửi; sự kiện `answer_feedback_submitted`
- [ ] **T309.2** `FE` — **`FeedbackControl`**: 👍 → gửi ngay, hiện lời cảm ơn; 👎 → mở 4 lý do (Chip), chọn lý do thì gửi; nút có `aria-pressed` / `aria-expanded`

## 5. Trường hợp biên và lưu ý

- Xem các trường hợp lỗi ở mục 3 (mã lỗi) và các tiêu chí nghiệm thu ở mục 6.

## 6. Tiêu chí nghiệm thu

- [ ] **AC-309.1** — *Given* một câu trả lời hoàn tất, *When* tôi bấm 👍, *Then* phản hồi được ghi và tôi thấy lời cảm ơn; sinh đúng 1 sự kiện `answer_feedback_submitted`.
- [ ] **AC-309.2** — *Given* tôi bấm 👎, *When* danh sách lý do hiện ra (Sai thông tin / Thiếu ý / Sai nguồn / Khác), *Then* chọn một lý do sẽ gửi phản hồi kèm lý do.

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Kiểm chứng AC-309.1 như mô tả ở mục 6 | Integration | AC-309.1 |
| Kiểm chứng AC-309.2 như mô tả ở mục 6 | Integration | AC-309.2 |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
