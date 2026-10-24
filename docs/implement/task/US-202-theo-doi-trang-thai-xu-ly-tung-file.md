# US-202 · Theo dõi trạng thái xử lý từng file

| Thuộc tính | Giá trị |
|---|---|
| Loại | User story · E2. Kho tài liệu |
| Sprint | Sprint 1 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | P0 |
| Story point | 3 `[Đề xuất]` |
| Vai trò thực hiện | Backend, Frontend |
| Phụ thuộc | EN-04 (pipeline xử lý) |
| Chặn bởi | — |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

> Là **chuyên viên BD**, tôi muốn thấy trạng thái từng file (đang tải, đang xử lý, sẵn sàng, lỗi), để biết khi nào có thể hỏi về file đó.

**Truy vết:** BR-001 · UCD-06, UCD-09 · NFR-03 · LG-07

**Thiết kế giao diện:** [`workspace.html`](../../04-design/UI_UX_design/workspace.html)

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** Những gì không được liệt kê ở mục 4 và mục 6.

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

**API**

| # | Endpoint | Request | Response 2xx | Lỗi (code) | Story |
|---|---|---|---|---|---|
| D2 | `GET /api/v1/documents?q&status&cursor&limit` | — | `{items: DocumentDto[], nextCursor}` | — | US-202, 203 |
| D5 | `POST /api/v1/documents/{id}/retry` | — | 202 | 403 · 409 INVALID_STATE | US-202 |

**Bảng CSDL** (trích migration `0001_init`, dev_tasks.md §0.3)

```sql
CREATE INDEX ix_doc_status ON documents.document (library_id, status);

CREATE INDEX ix_doc_name_trgm ON documents.document USING gin (file_name gin_trgm_ops);
```

**Mã lỗi**

| code | HTTP | Thông điệp FE (`vi.ts`) | Hành động FE |
|---|---|---|---|
| INVALID_STATE | 409 | — | Làm mới dữ liệu |

## 4. Công việc chi tiết

- [ ] **T202.1** `BE` — **`GET /documents`**: Lọc `removed_at IS NULL`; `canRemove = PermissionPolicy.can(user,"documents:remove",doc)`; phân trang theo cursor `(uploaded_at, id)`
- [ ] **T202.2** `BE` — **`POST /documents/{id}/retry`**: Chỉ cho trạng thái `ERROR`; chuyển `PROCESSING` + tạo job mới
- [ ] **T202.3** `FE` — **Polling**: `useDocuments`: `refetchInterval = 3000` khi có file `UPLOADING` / `PROCESSING`, ngược lại tắt; dừng khi `document.hidden`
- [ ] **T202.4** `FE` — **`DocumentItem`**: Đủ trạng thái như prototype: icon, Badge, thông điệp theo `errorCode`, menu ⋯ (Thử lại / Gỡ)
- [ ] **T202.5** `FE` — **Toast khi sẵn sàng**: So sánh dữ liệu cũ / mới: `PROCESSING → READY` → toast "“{file}” đã sẵn sàng để hỏi"

## 5. Trường hợp biên và lưu ý

- Xem các trường hợp lỗi ở mục 3 (mã lỗi) và các tiêu chí nghiệm thu ở mục 6.

## 6. Tiêu chí nghiệm thu

- [ ] **AC-202.1** — *Given* một file 50 MB / 300 trang đã tải xong, *When* xử lý kết thúc, *Then* trạng thái chuyển "Sẵn sàng" chậm nhất 5 phút sau khi tải lên (AC-001) và file được dùng ngay cho câu hỏi tiếp theo.
- [ ] **AC-202.2** — *Given* một file đang "Đang xử lý", *When* tôi đặt câu hỏi, *Then* câu trả lời chỉ dùng file "Sẵn sàng" và có ghi chú "1 tài liệu đang được xử lý, chưa được dùng".
- [ ] **AC-202.3** — *Given* xử lý thất bại (mật khẩu, file hỏng), *When* trạng thái là "Lỗi", *Then* tôi thấy lý do bằng ngôn ngữ thường ngày và nút "Thử lại" (EC-09, EC-11).

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Kiểm chứng AC-202.1 như mô tả ở mục 6 | Integration | AC-202.1 |
| Kiểm chứng AC-202.2 như mô tả ở mục 6 | Integration | AC-202.2 |
| Kiểm chứng AC-202.3 như mô tả ở mục 6 | Integration | AC-202.3 |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
