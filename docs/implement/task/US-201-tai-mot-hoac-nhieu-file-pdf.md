# US-201 · Tải một hoặc nhiều file PDF

| Thuộc tính | Giá trị |
|---|---|
| Loại | User story · E2. Kho tài liệu |
| Sprint | Sprint 1 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | P0 |
| Story point | 5 `[Đề xuất]` |
| Vai trò thực hiện | Backend, Frontend |
| Phụ thuộc | EN-02 (storage), EN-11 (component UploadDropzone, DocumentItem) |
| Chặn bởi | PQ-001 (kho chung) — tạm theo PD-01 |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

> Là **chuyên viên BD**, tôi muốn kéo-thả một hoặc nhiều file PDF vào sản phẩm, để các file đó trở thành nguồn cho câu trả lời.

**Truy vết:** BR-001 · UCD-04, UCD-05 · EC-04, EC-07, EC-08 · NFR-06 · REL-05

**Thiết kế giao diện:** [`workspace.html`](../../04-design/UI_UX_design/workspace.html)

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** OCR cho file scan, định dạng khác PDF (để giai đoạn sau).

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

**API**

| # | Endpoint | Request | Response 2xx | Lỗi (code) | Story |
|---|---|---|---|---|---|
| D1 | `POST /api/v1/documents?force=false` | multipart `file` | 202 `DocumentDto` | 413 FILE_TOO_LARGE · 415 FILE_NOT_PDF · 409 DUPLICATE_DOCUMENT `{existingId, uploadedAt}` · 429 | US-201, 206 |

**Bảng CSDL** (trích migration `0001_init`, dev_tasks.md §0.3)

```sql
CREATE INDEX ix_doc_status ON documents.document (library_id, status);

CREATE INDEX ix_doc_name_trgm ON documents.document USING gin (file_name gin_trgm_ops);

CREATE INDEX ix_job_ready ON platform.job (run_after) WHERE status = 'queued';
```

**Cấu hình**

| Biến | Mặc định |
|---|---|
| `MAX_UPLOAD_MB` | `50` |

**Mã lỗi**

| code | HTTP | Thông điệp FE (`vi.ts`) | Hành động FE |
|---|---|---|---|
| RATE_LIMITED | 429 | "Bạn thao tác quá nhanh, thử lại sau {retryAfter} giây." | Toast |
| FILE_NOT_PDF | 415 | "Chỉ hỗ trợ file PDF." | Toast theo từng file |
| FILE_TOO_LARGE | 413 | "File vượt 50 MB. Hãy tách file hoặc liên hệ trưởng nhóm." | Toast theo từng file |
| DUPLICATE_DOCUMENT | 409 | "File này đã có trong kho (tải lên ngày {date}). Vẫn tải?" | ConfirmDialog → gửi lại với `force=true` |

**Sự kiện phân tích** (danh sách cho phép, không có trường nội dung)

| name | Nguồn | props cho phép |
|---|---|---|
| `document_upload_started` | FE | `file_size_mb: number`, `batch_size: int` |
| `document_upload_failed` | FE / BE | `reason: not_pdf \| too_large \| network \| password \| corrupt` |

## 4. Công việc chi tiết

- [ ] **T201.1** `BE` — **Port + adapter storage**: `ports/storage.py`: `put(key, stream, size) -> None`, `open(key, byte_range=None)`, `delete(key)`. `adapters/storage/s3.py` (aioboto3; SSE theo `S3_SSE`; tương thích MinIO)
- [ ] **T201.2** `BE` — **`UploadPolicy`**: `domain/documents/upload_policy.py`: `validate(file_name, size, head_bytes)`. Lỗi `FILE_TOO_LARGE` nếu size > `MAX_UPLOAD_MB`; `FILE_NOT_PDF` nếu 5 byte đầu ≠ `%PDF-`
- [ ] **T201.3** `BE` — **`POST /documents`**: Stream multipart vào file tạm, vừa nhận vừa tính SHA-256 (không đọc cả file vào RAM); kiểm tra dung lượng cả trong lúc stream (dừng khi vượt)
- [ ] **T201.4** `BE` — **`DocumentService.upload`**: (1) kiểm tra trùng: `SELECT … WHERE library_id=$1 AND content_hash=$2 AND removed_at IS NULL`; có và `force=false` → 409 `DUPLICATE_DOCUMENT`. (2) `storage.put("library/{lib}/doc/{id}.pdf")`. (3) **một giao dịch:** `INSERT document(status=PROCESSING)` + `INSERT job(process_document,{document_id})` + `NOTIFY jobs`. (4) audit `upload`. Bước 3 lỗi → object mồ côi; job dọn dẹp hằng ngày xoá object không có dòng `document`
- [ ] **T201.5** `FE` — **`UploadDropzone` + `useUploadQueue`**: Nhận nhiều file (chọn hoặc kéo-thả); kiểm tra ở client (đuôi `.pdf` hoặc mime, ≤ 50 MB) trước khi gửi; hàng đợi tải tối đa 3 file song song; `XMLHttpRequest` để có `upload.onprogress`
- [ ] **T201.6** `FE` — **Thử lại khi mất mạng**: Bắt `offline` hoặc lỗi mạng → trạng thái `paused`; thử lại 2 s / 4 s / 8 s; quá 3 lần → `upload_failed` kèm nút "Thử lại" (EC-04)
- [ ] **T201.7** `FE` — **Sự kiện**: `document_upload_started`, `document_upload_failed` (§0.7)

## 5. Trường hợp biên và lưu ý

- File đổi đuôi `.pdf` nhưng không phải PDF → BE trả 415 dù FE đã cho qua.
- Mất kết nối giữa lúc tải: không để lại dòng `document` mồ côi (object mồ côi do job dọn dẹp xoá).
- Tải 10 file một lúc: tối đa 3 file tải song song, các file còn lại xếp hàng.

## 6. Tiêu chí nghiệm thu

- [ ] **AC-201.1** — *Given* tôi ở màn hình làm việc, *When* tôi thả 1 file PDF dạng văn bản ≤ 50 MB (hoặc chọn bằng nút "Tải tài liệu"), *Then* file xuất hiện trong danh sách với trạng thái "Đang tải lên" và % tiến độ.
- [ ] **AC-201.2** — *Given* tôi chọn đồng thời 10 file hợp lệ, *When* tôi thả vào, *Then* cả 10 file vào hàng đợi, mỗi file có trạng thái riêng.
- [ ] **AC-201.3** — *Given* một file không phải PDF hoặc > 50 MB, *When* tôi thả vào, *Then* file đó bị từ chối trước khi tải lên, kèm lý do đúng; các file hợp lệ khác vẫn được tải.
- [ ] **AC-201.4** — *Given* mất mạng khi đang tải, *When* có mạng lại, *Then* file tự tải tiếp (tối đa 3 lần thử); quá 3 lần thì báo lỗi kèm nút "Thử lại" (EC-04).

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Thả 1 file 50 MB → có % tiến độ, rồi "Đang xử lý" | E2E | AC-201.1 |
| Thả 10 file → 10 dòng, mỗi dòng một trạng thái | E2E | AC-201.2 |
| File `.png` đổi đuôi `.pdf` → BE trả 415; file 51 MB → FE chặn, BE trả 413 | Unit + integration | AC-201.3 |
| Ngắt mạng (Playwright `context.setOffline`) khi đang tải → `paused` → bật lại → xong | E2E | AC-201.4 |
| Giao dịch `document` + `job`: lỗi giữa chừng → không có `document` mồ côi | Integration | SAD §3.2.2 |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
