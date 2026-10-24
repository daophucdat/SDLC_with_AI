# US-204 · Gỡ tài liệu

| Thuộc tính | Giá trị |
|---|---|
| Loại | User story · E2. Kho tài liệu |
| Sprint | Sprint 3 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | P1 |
| Story point | 5 `[Đề xuất]` |
| Vai trò thực hiện | Backend, Frontend |
| Phụ thuộc | US-203, EN-09 (job purge) |
| Chặn bởi | PQ-002 (ai được gỡ) — tạm theo PD-02 |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

> Là **chuyên viên BD**, tôi muốn gỡ một tài liệu tôi đã tải lên, để tài liệu lỗi thời không còn được dùng trong câu trả lời mới.

**Truy vết:** BR-005, RUL-003 · UCD-11 → 13, UCD-15 · PD-02 · SEC-06

**Thiết kế giao diện:** [`workspace.html (menu ⋯ → Gỡ khỏi kho, vai trò Trưởng nhóm)`](../../04-design/UI_UX_design/workspace.html)

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** Khôi phục tài liệu đã gỡ; phân quyền theo từng tài liệu (BR-013).

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

**API**

| # | Endpoint | Request | Response 2xx | Lỗi (code) | Story |
|---|---|---|---|---|---|
| D4 | `DELETE /api/v1/documents/{id}` | — | 202 | 403 FORBIDDEN · 404 | US-204 |

**Bảng CSDL** (trích migration `0001_init`, dev_tasks.md §0.3)

```sql
CREATE INDEX ix_doc_status ON documents.document (library_id, status);

CREATE INDEX ix_doc_name_trgm ON documents.document USING gin (file_name gin_trgm_ops);

CREATE INDEX ix_job_ready ON platform.job (run_after) WHERE status = 'queued';

CREATE TABLE platform.audit_log (
  id bigint GENERATED ALWAYS AS IDENTITY,
  ts timestamptz NOT NULL DEFAULT now(),
  actor_id uuid, action text NOT NULL, target_type text, target_id text, ip inet,
  PRIMARY KEY (id, ts)
) PARTITION BY RANGE (ts);
```

**Cấu hình**

| Biến | Mặc định |
|---|---|
| `PURGE_DEADLINE_HOURS` | `24` |

**Mã lỗi**

| code | HTTP | Thông điệp FE (`vi.ts`) | Hành động FE |
|---|---|---|---|
| FORBIDDEN_ROLE | 403 | "Bạn chưa được cấp quyền dùng công cụ này. Liên hệ trưởng nhóm BD." | Trang `/denied` |
| FORBIDDEN | 403 | "Bạn không có quyền thực hiện thao tác này." | Toast |
| DOC_NOT_FOUND | 404 | "Tài liệu này đã được gỡ khỏi kho." | Vùng nguồn hiển thị trạng thái đã gỡ |

**Sự kiện phân tích** (danh sách cho phép, không có trường nội dung)

| name | Nguồn | props cho phép |
|---|---|---|
| `document_removed` | BE | `role: uploader \| lead`, `doc_age_days: int` |

## 4. Công việc chi tiết

- [ ] **T204.1** `BE` — **`DocumentService.remove`**: `PermissionPolicy.can(user, "documents:remove", doc)` (người tải lên hoặc LEAD) → 403 nếu không có quyền. Trong 1 giao dịch: `removed_at=now(), removed_by, status='REMOVED'` + job `purge_document` + audit `remove`; sự kiện `document_removed {role, doc_age_days}`
- [ ] **T204.2** `BE` — **Job `purge_document`**: Xoá object (`storage.delete`); `DELETE FROM documents.text_chunk / document_page WHERE document_id=$1`; giữ dòng `document` (tombstone); `purged_at=now()`; thử lại 5 lần
- [ ] **T204.3** `BE` — **Cảnh báo quá hạn**: Metric + cảnh báo khi có `removed_at < now() - 20h AND purged_at IS NULL` (SEC-06)
- [ ] **T204.4** `FE` — **Menu + ConfirmDialog**: Mục "Gỡ khỏi kho" chỉ hiện khi `canRemove`; hộp xác nhận theo prototype; gỡ xong thì cập nhật cache ngay (optimistic update) + toast "Đã gỡ “{file}”"
- [ ] **T204.5** `FE` — **Trích dẫn cũ**: Khi tài liệu biến khỏi `useDocuments`, các `CitationDto` cùng `documentId` trong hội thoại hiện tại được đánh dấu `removed=true`

## 5. Trường hợp biên và lưu ý

- Hai người cùng gỡ một tài liệu → lần thứ hai nhận 404, FE làm mới danh sách.
- Tài liệu đang được trích dẫn trong hội thoại hiện tại → trích dẫn bị gạch, không mở được (EC-15).

## 6. Tiêu chí nghiệm thu

- [ ] **AC-204.1** — *Given* tôi là người tải lên (hoặc là Trưởng nhóm BD), *When* tôi mở menu của tài liệu, *Then* có mục "Gỡ khỏi kho"; với người khác thì mục này không có (PD-02).
- [ ] **AC-204.2** — *Given* tôi chọn "Gỡ khỏi kho", *When* hộp xác nhận hiện ra, *Then* nó nêu rõ ảnh hưởng tới cả đội và focus mặc định ở "Huỷ".
- [ ] **AC-204.3** — *Given* tôi xác nhận gỡ, *When* hỏi 10 câu hỏi kiểm thử về nội dung riêng của tài liệu đó, *Then* 0/10 câu trả lời trích từ nó (AC-005).
- [ ] **AC-204.4** — *Given* tài liệu đã bị gỡ, *When* qua 24 giờ, *Then* file và nội dung đã bị xoá vĩnh viễn khỏi kho lưu trữ và chỉ mục (SEC-06).
- [ ] **AC-204.5** — *Given* người không có quyền gọi API gỡ, *When* yêu cầu đến máy chủ, *Then* bị từ chối `403`.

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Thành viên không thấy "Gỡ" trên tài liệu của người khác; Trưởng nhóm thấy | E2E (2 tài khoản) | AC-204.1 |
| Focus mặc định ở "Huỷ"; Esc để đóng | E2E | AC-204.2 |
| Sau khi gỡ: 0/10 câu hỏi trích từ tài liệu đó | Integration + đánh giá | AC-204.3 |
| Job purge: object và đoạn văn bản không còn; `purged_at` có giá trị | Integration | AC-204.4 |
| Gọi API gỡ bằng tài khoản không có quyền → 403 | Security | AC-204.5 |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
