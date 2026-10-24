# US-206 · Cảnh báo file trùng

| Thuộc tính | Giá trị |
|---|---|
| Loại | User story · E2. Kho tài liệu |
| Sprint | Sprint 4 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | P2 |
| Story point | 2 `[Đề xuất]` |
| Vai trò thực hiện | Backend, Frontend |
| Phụ thuộc | US-201 (tính mã băm nội dung) |
| Chặn bởi | — |
| Feature flag | `duplicate` |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

> Là **chuyên viên BD**, tôi muốn được cảnh báo khi tải lên một file trùng với file đã có, để kho không có bản trùng làm câu trả lời bị lặp.

**Truy vết:** SN-006 · UCD-08 · EC-12 · `[PRD-new]`

**Thiết kế giao diện:** [`workspace.html (tải lại file trùng tên)`](../../04-design/UI_UX_design/workspace.html)

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** Những gì không được liệt kê ở mục 4 và mục 6.

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

**Bảng CSDL** (trích migration `0001_init`, dev_tasks.md §0.3)

```sql
CREATE INDEX ix_doc_status ON documents.document (library_id, status);

CREATE INDEX ix_doc_name_trgm ON documents.document USING gin (file_name gin_trgm_ops);
```

**Mã lỗi**

| code | HTTP | Thông điệp FE (`vi.ts`) | Hành động FE |
|---|---|---|---|
| DUPLICATE_DOCUMENT | 409 | "File này đã có trong kho (tải lên ngày {date}). Vẫn tải?" | ConfirmDialog → gửi lại với `force=true` |

## 4. Công việc chi tiết

- [ ] `FE` nhận 409 `DUPLICATE_DOCUMENT` → ConfirmDialog (`danger=false`, nhãn "Vẫn tải") → gửi lại với `force=true`.
- [ ] `BE` đã có ở T201.4

## 5. Trường hợp biên và lưu ý

- Xem các trường hợp lỗi ở mục 3 (mã lỗi) và các tiêu chí nghiệm thu ở mục 6.

## 6. Tiêu chí nghiệm thu

- [ ] **AC-206.1** — *Given* một file có nội dung trùng 100% với tài liệu chưa gỡ, *When* tôi tải lên, *Then* hệ thống hỏi "File này đã có trong kho (tải lên ngày …). Vẫn tải?" trong 100% lần thử.
- [ ] **AC-206.2** — *Given* tôi chọn "Vẫn tải", *When* xác nhận, *Then* file được tải như bình thường.

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Kiểm chứng AC-206.1 như mô tả ở mục 6 | Integration | AC-206.1 |
| Kiểm chứng AC-206.2 như mô tả ở mục 6 | Integration | AC-206.2 |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
