# US-305 · Mở đúng trang nguồn

| Thuộc tính | Giá trị |
|---|---|
| Loại | User story · E3. Hỏi đáp có dẫn nguồn |
| Sprint | Sprint 3 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | P1 |
| Story point | 5 `[Đề xuất]` |
| Vai trò thực hiện | Backend, Frontend, QA |
| Phụ thuộc | US-303; endpoint file có Range (SAD §2.4) |
| Chặn bởi | — |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

> Là **chuyên viên BD**, tôi muốn bấm vào trích dẫn để mở đúng trang PDF cạnh khung chat, để kiểm chứng mà không rời cuộc hội thoại.

**Truy vết:** BR-007, SN-005 · UCD-22 · NFR-05

**Thiết kế giao diện:** [`workspace.html?demo=answer`](../../04-design/UI_UX_design/workspace.html?demo=answer)

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** Những gì không được liệt kê ở mục 4 và mục 6.

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

**API**

| # | Endpoint | Request | Response 2xx | Lỗi (code) | Story |
|---|---|---|---|---|---|
| D3 | `GET /api/v1/documents/{id}/file` | header `Range` | 206 / 200 `application/pdf` | 404 DOC_NOT_FOUND (cả khi đã gỡ) | US-305 |

**Bảng CSDL** (trích migration `0001_init`, dev_tasks.md §0.3)

```sql
CREATE INDEX ix_doc_status ON documents.document (library_id, status);

CREATE INDEX ix_doc_name_trgm ON documents.document USING gin (file_name gin_trgm_ops);
```

**Mã lỗi**

| code | HTTP | Thông điệp FE (`vi.ts`) | Hành động FE |
|---|---|---|---|
| DOC_NOT_FOUND | 404 | "Tài liệu này đã được gỡ khỏi kho." | Vùng nguồn hiển thị trạng thái đã gỡ |

**Sự kiện phân tích** (danh sách cho phép, không có trường nội dung)

| name | Nguồn | props cho phép |
|---|---|---|
| `citation_clicked` | FE | `citation_index: int`, `doc_removed: bool` |

## 4. Công việc chi tiết

- [ ] **T305.1** `BE` — **`GET /documents/{id}/file`**: Kiểm quyền + `removed_at IS NULL` (ngược lại 404); proxy stream từ storage, hỗ trợ `Range` (206, `Accept-Ranges: bytes`, `Content-Range`); `Cache-Control: private, max-age=300`
- [ ] **T305.2** `FE` — **`SourcePanel` (lazy)**: `React.lazy` + `pdfjs-dist`; `getDocument({url, rangeChunkSize: 65536, disableAutoFetch: true})` để chỉ tải phần cần; render trang `page` và `page ± 1`; huỷ `PDFDocumentProxy` khi đóng panel
- [ ] **T305.3** `FE` — **Tô sáng đoạn**: Bật text layer; tìm `excerpt` (đã chuẩn hoá khoảng trắng, NFC) trong text của trang; bao vùng tìm thấy bằng `<mark>`; không tìm thấy thì chỉ mở đúng trang
- [ ] **T305.4** `FE` — **Trạng thái và điều khiển**: URL hash `#src=<docId>:<page>`; Esc để đóng; nút trang trước / sau; `CitationChip` đang mở có `aria-pressed=true`; trích dẫn của tài liệu đã gỡ bị gạch và không bấm được (EC-15); 404 → "Tài liệu này vừa được gỡ khỏi kho" (EC-16)
- [ ] **T305.5** `FE` — **Sự kiện**: `citation_clicked {citation_index, doc_removed}`
- [ ] **T305.6** `QA` — **Đo NFR-05**: Playwright đo thời gian từ lúc bấm tới khi canvas trang được vẽ, với file 50 MB → p95 ≤ 2 s

## 5. Trường hợp biên và lưu ý

- File lớn: không tải cả file, chỉ tải các khoảng byte cần (Range).
- `excerpt` không khớp text layer (do PDF có ligature, xuống dòng) → vẫn mở đúng trang, không tô sáng.

## 6. Tiêu chí nghiệm thu

- [ ] **AC-305.1** — *Given* câu trả lời có trích dẫn `[1]`, *When* tôi bấm `[1]`, *Then* vùng nguồn mở đúng tài liệu, đúng trang, đoạn liên quan được tô sáng, trong ≤ 2 giây ở p95 với file ≤ 50 MB (NFR-05).
- [ ] **AC-305.2** — *Given* vùng nguồn đang mở, *When* tôi bấm `[2]`, *Then* vùng nguồn chuyển sang nguồn mới, không mở cửa sổ mới.
- [ ] **AC-305.3** — *Given* tài liệu của trích dẫn đã bị gỡ, *When* tôi xem câu trả lời, *Then* trích dẫn bị gạch, có chú thích "Tài liệu đã được gỡ" và không mở được (EC-15).

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Kiểm chứng AC-305.1 như mô tả ở mục 6 | Integration | AC-305.1 |
| Kiểm chứng AC-305.2 như mô tả ở mục 6 | Integration | AC-305.2 |
| Kiểm chứng AC-305.3 như mô tả ở mục 6 | Integration | AC-305.3 |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
