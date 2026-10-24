# US-401 · Trang số liệu hằng tuần

| Thuộc tính | Giá trị |
|---|---|
| Loại | User story · E4. Đo lường giá trị |
| Sprint | Sprint 4 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | P1 |
| Story point | 5 `[Đề xuất]` |
| Vai trò thực hiện | Backend, Frontend |
| Phụ thuộc | EN-08 |
| Chặn bởi | — |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

> Là **quản lý**, tôi muốn xem trang số liệu hằng tuần (người dùng hoạt động, số câu hỏi, tỉ lệ "không tìm thấy", tỉ lệ hữu ích, thời gian trả lời p95), để đánh giá MVP sau 4 tuần.

**Truy vết:** SN-002 · UCD-26 · M-003 · KR1.2, KR3.1, KR3.2

**Thiết kế giao diện:** [`metrics.html`](../../04-design/UI_UX_design/metrics.html)

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** Biểu đồ; xuất số liệu.

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

**API**

| # | Endpoint | Request | Response 2xx | Lỗi (code) | Story |
|---|---|---|---|---|---|
| M1 | `GET /api/v1/metrics/weekly?weeks=4` | — | `WeeklyMetricDto[]` | 403 | US-401 |

**Bảng CSDL** (trích migration `0001_init`, dev_tasks.md §0.3)

```sql
CREATE INDEX ix_event_name_ts ON analytics.event (name, ts);

CREATE TABLE analytics.daily_rollup (day date, metric text, value numeric NOT NULL, PRIMARY KEY (day, metric));
```

**Mã lỗi**

| code | HTTP | Thông điệp FE (`vi.ts`) | Hành động FE |
|---|---|---|---|
| FORBIDDEN_ROLE | 403 | "Bạn chưa được cấp quyền dùng công cụ này. Liên hệ trưởng nhóm BD." | Trang `/denied` |
| FORBIDDEN | 403 | "Bạn không có quyền thực hiện thao tác này." | Toast |

**Sự kiện phân tích** (danh sách cho phép, không có trường nội dung)

| name | Nguồn | props cho phép |
|---|---|---|
| `question_submitted` | BE | `language`, `question_length: int`, `ready_doc_count: int`, `is_suggested: bool`, `turn_index: int` |
| `answer_completed` | BE | `latency_ms`, `first_token_ms`, `citation_count`, `distinct_docs_cited`, `is_not_found: bool`, `not_found_reason` |
| `answer_feedback_submitted` | BE | `value`, `reason` |

## 4. Công việc chi tiết

- [ ] **T401.1** `BE` — **Job `rollup_metrics` (01:00 hằng ngày)**: Tính cho ngày hôm trước và ghi `daily_rollup`: `active_users` (số `user_id_hash` khác nhau có `question_submitted`), `questions`, `not_found`, `answers`, `helpful`, `feedback_total`, `p95_latency_ms` (`percentile_cont(0.95)` trên `answer_completed.latency_ms`), `errors`
- [ ] **T401.2** `BE` — **`GET /metrics/weekly`**: Gộp theo tuần ISO (thứ Hai → Chủ nhật); `wauRate = active_users_week / số user active trong app_user`; quyền `metrics:view`
- [ ] **T401.3** `FE` — **`MetricsPage`**: Theo `metrics.html`: ô chỉ số (đạt / không đạt so với OKR), bảng theo tuần, chọn 4 / 8 / 12 tuần; menu "Số liệu" chỉ hiện khi có quyền

## 5. Trường hợp biên và lưu ý

- Xem các trường hợp lỗi ở mục 3 (mã lỗi) và các tiêu chí nghiệm thu ở mục 6.

## 6. Tiêu chí nghiệm thu

- [ ] **AC-401.1** — *Given* tôi là Trưởng nhóm BD hoặc Quản lý, *When* mở trang số liệu và chọn 4 / 8 / 12 tuần, *Then* tôi thấy 5 chỉ số theo từng tuần, so với mục tiêu OKR.
- [ ] **AC-401.2** — *Given* tôi là Thành viên BD, *When* truy cập trang số liệu, *Then* mục menu không hiện và API trả `403`.
- [ ] **AC-401.3** — *Given* dữ liệu sự kiện, *When* tính chỉ số, *Then* không dùng nội dung câu hỏi; người dùng chỉ được đếm qua mã băm.

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Kiểm chứng AC-401.1 như mô tả ở mục 6 | Integration | AC-401.1 |
| Kiểm chứng AC-401.2 như mô tả ở mục 6 | Integration | AC-401.2 |
| Kiểm chứng AC-401.3 như mô tả ở mục 6 | Integration | AC-401.3 |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
