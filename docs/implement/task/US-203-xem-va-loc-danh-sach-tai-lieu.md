# US-203 · Xem và lọc danh sách tài liệu

| Thuộc tính | Giá trị |
|---|---|
| Loại | User story · E2. Kho tài liệu |
| Sprint | Sprint 3 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | P1 |
| Story point | 3 `[Đề xuất]` |
| Vai trò thực hiện | Backend, Frontend |
| Phụ thuộc | US-201 |
| Chặn bởi | — |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

> Là **chuyên viên BD**, tôi muốn xem danh sách tài liệu (tên, số trang, người tải, ngày tải), để biết câu trả lời dựa trên những tài liệu nào.

**Truy vết:** BR-004 · UCD-10, UCD-14

**Thiết kế giao diện:** [`workspace.html`](../../04-design/UI_UX_design/workspace.html)

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

## 4. Công việc chi tiết

- [ ] **T203.1** `BE` — **Tham số `q`**: `q` ≥ 2 ký tự → `file_name ILIKE '%'
- [ ] **T203.2** `FE` — **Ô lọc**: Debounce 250 ms; < 2 ký tự thì không lọc; không có kết quả → EmptyState kèm nút "Xoá bộ lọc"; ở chế độ thu gọn (< 1280 px) chỉ hiện icon và tooltip

## 5. Trường hợp biên và lưu ý

- Xem các trường hợp lỗi ở mục 3 (mã lỗi) và các tiêu chí nghiệm thu ở mục 6.

## 6. Tiêu chí nghiệm thu

- [ ] **AC-203.1** — *Given* kho có N tài liệu, *When* tôi mở màn hình làm việc, *Then* danh sách hiển thị đủ N tài liệu với tên file, số trang, người tải, ngày tải (AC-004).
- [ ] **AC-203.2** — *Given* tôi gõ ≥ 2 ký tự vào ô lọc, *When* có tài liệu khớp, *Then* danh sách chỉ còn các tài liệu khớp; không có thì hiện "Không có tài liệu nào khớp" kèm nút xoá bộ lọc.

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Kiểm chứng AC-203.1 như mô tả ở mục 6 | Integration | AC-203.1 |
| Kiểm chứng AC-203.2 như mô tả ở mục 6 | Integration | AC-203.2 |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
