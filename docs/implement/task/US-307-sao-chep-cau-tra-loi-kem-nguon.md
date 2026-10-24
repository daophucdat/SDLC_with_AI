# US-307 · Sao chép câu trả lời kèm nguồn

| Thuộc tính | Giá trị |
|---|---|
| Loại | User story · E3. Hỏi đáp có dẫn nguồn |
| Sprint | Sprint 3 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | P1 |
| Story point | 2 `[Đề xuất]` |
| Vai trò thực hiện | Frontend |
| Phụ thuộc | US-303 |
| Chặn bởi | — |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

> Là **chuyên viên BD**, tôi muốn sao chép câu trả lời kèm danh sách nguồn, để dán vào email hoặc tài liệu đề xuất.

**Truy vết:** SN-001 · UCD-24 · sự kiện `answer_copied`

**Thiết kế giao diện:** [`workspace.html?demo=answer`](../../04-design/UI_UX_design/workspace.html?demo=answer)

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** Những gì không được liệt kê ở mục 4 và mục 6.

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

**Sự kiện phân tích** (danh sách cho phép, không có trường nội dung)

| name | Nguồn | props cho phép |
|---|---|---|
| `answer_copied` | FE | `with_sources: bool` |

## 4. Công việc chi tiết

- [ ] **T307.1** `FE` — **Nút sao chép**: `navigator.clipboard.writeText(text + "\n\nNguồn:\n" + lines)`; lỗi quyền → toast hướng dẫn sao chép thủ công; sự kiện `answer_copied {with_sources: true}`

## 5. Trường hợp biên và lưu ý

- Xem các trường hợp lỗi ở mục 3 (mã lỗi) và các tiêu chí nghiệm thu ở mục 6.

## 6. Tiêu chí nghiệm thu

- [ ] **AC-307.1** — *Given* một câu trả lời hoàn tất, *When* tôi bấm "Sao chép kèm nguồn", *Then* clipboard chứa câu trả lời và danh sách "Tên tài liệu — trang X".
- [ ] **AC-307.2** — *Given* trình duyệt chặn ghi clipboard, *When* tôi bấm sao chép, *Then* tôi được báo hãy chọn và sao chép thủ công.

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Kiểm chứng AC-307.1 như mô tả ở mục 6 | Integration | AC-307.1 |
| Kiểm chứng AC-307.2 như mô tả ở mục 6 | Integration | AC-307.2 |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
