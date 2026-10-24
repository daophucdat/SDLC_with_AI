# EN-08 · Sự kiện phân tích

| Thuộc tính | Giá trị |
|---|---|
| Loại | Enabler · EN. Enabler kỹ thuật |
| Sprint | Sprint 3 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | Enabler (bắt buộc cho các story phụ thuộc) |
| Story point | 3 `[Đề xuất]` |
| Vai trò thực hiện | Backend |
| Phụ thuộc | EN-02 |
| Chặn bởi | — |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

Bảng `analytics.event` phân vùng theo tháng; danh sách thuộc tính cho phép; `user_id_hash` bằng HMAC; `POST /events`

**Truy vết:** PRD §5.2, LG-15

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** Những gì không được liệt kê ở mục 4 và mục 6.

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

**API**

| # | Endpoint | Request | Response 2xx | Lỗi (code) | Story |
|---|---|---|---|---|---|
| E1 | `POST /api/v1/events` | `{name, props}` | 202 | 400 EVENT_INVALID | EN-08 |

**Bảng CSDL** (trích migration `0001_init`, dev_tasks.md §0.3)

```sql
CREATE INDEX ix_event_name_ts ON analytics.event (name, ts);
```

**Cấu hình**

| Biến | Mặc định |
|---|---|
| `ANALYTICS_HMAC_KEY` | — (secret) |

**Sự kiện phân tích** (danh sách cho phép, không có trường nội dung)

| name | Nguồn | props cho phép |
|---|---|---|
| `session_started` | BE (callback) | `is_first_session: bool` |
| `access_denied` | BE | `reason: enum` |
| `document_upload_started` | FE | `file_size_mb: number`, `batch_size: int` |
| `document_upload_failed` | FE / BE | `reason: not_pdf \| too_large \| network \| password \| corrupt` |
| `document_processing_completed` | worker | `page_count: int`, `duration_ms: int`, `status: ready \| no_text \| error` |
| `document_removed` | BE | `role: uploader \| lead`, `doc_age_days: int` |
| `question_submitted` | BE | `language`, `question_length: int`, `ready_doc_count: int`, `is_suggested: bool`, `turn_index: int` |
| `answer_completed` | BE | `latency_ms`, `first_token_ms`, `citation_count`, `distinct_docs_cited`, `is_not_found: bool`, `not_found_reason` |
| `answer_failed` | BE | `error_type: timeout \| service_error \| network` |
| `answer_stopped` | BE | `elapsed_ms: int` |
| `citation_clicked` | FE | `citation_index: int`, `doc_removed: bool` |
| `answer_copied` | FE | `with_sources: bool` |
| `answer_feedback_submitted` | BE | `value`, `reason` |

## 4. Công việc chi tiết

- [ ] **T-EN08.1** `DB` — **Phân vùng**: Job tạo partition `analytics.event_YYYYMM` trước 2 tháng; xoá partition cũ hơn 13 tháng (OQ-016)
- [ ] **T-EN08.2** `BE` — **`AnalyticsSink`**: `adapters/analytics/postgres_sink.py`: ghi bất đồng bộ qua hàng đợi trong bộ nhớ (lô 50 hoặc 2 s); lỗi ghi không được làm hỏng request
- [ ] **T-EN08.3** `BE` — **Danh sách cho phép**: Kiểm tra theo §0.7 (tên, khoá, kiểu); dư khoá hoặc sai kiểu → `EVENT_INVALID`; unit test chứng minh không thể ghi `text` / `content` / `question` / `answer` / `excerpt`
- [ ] **T-EN08.4** `BE` — **`POST /events`**: Chỉ nhận các sự kiện có nguồn FE (`document_upload_*`, `citation_clicked`, `answer_copied`); giới hạn 60 sự kiện / phút / người

## 5. Trường hợp biên và lưu ý

- Xem các trường hợp lỗi ở mục 3 (mã lỗi) và các tiêu chí nghiệm thu ở mục 6.

## 6. Tiêu chí nghiệm thu

- [ ] 13 sự kiện của PRD §5.2 được ghi; sự kiện có thuộc tính lạ bị từ chối

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Kiểm chứng tiêu chí hoàn thành ở mục 6 | Integration / báo cáo | EN-08 |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
