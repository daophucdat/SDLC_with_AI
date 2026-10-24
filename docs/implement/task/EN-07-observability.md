# EN-07 · Observability

| Thuộc tính | Giá trị |
|---|---|
| Loại | Enabler · EN. Enabler kỹ thuật |
| Sprint | Sprint 4 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | Enabler (bắt buộc cho các story phụ thuộc) |
| Story point | 5 `[Đề xuất]` |
| Vai trò thực hiện | Backend, DevOps |
| Phụ thuộc | EN-02 |
| Chặn bởi | — |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

OpenTelemetry (trace 8 span), metrics Prometheus, log JSON có lọc nội dung, 9 cảnh báo

**Truy vết:** SAD §4.3, QAS-06, QAS-11, LG-15, LG-17

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** Những gì không được liệt kê ở mục 4 và mục 6.

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

**API**

| # | Endpoint | Request | Response 2xx | Lỗi (code) | Story |
|---|---|---|---|---|---|
| H1 | `GET /healthz`, `GET /readyz` | — | 200 / 503 | — | EN-07 |

## 4. Công việc chi tiết

- [ ] **T-EN07.1** `BE` — **Tracing**: OTel SDK + instrument FastAPI, SQLAlchemy, httpx; span thủ công: `auth`, `retrieve.embed`, `retrieve.vector`, `retrieve.fts`, `llm.first_token`, `llm.stream`, `citations.validate`, `db.commit`; thuộc tính span chỉ là số đếm và thời gian
- [ ] **T-EN07.2** `BE` — **Metrics**: `/metrics` (prometheus-client): các metric ở SAD §4.3
- [ ] **T-EN07.3** `BE` — **Lọc log**: Processor structlog bỏ các khoá `text`, `content`, `question`, `answer`, `excerpt`, `prompt`; tắt log body ở access log; test: gửi câu hỏi có chuỗi đánh dấu `ZZZ-SECRET` → chuỗi đó không có trong log, span hay sự kiện
- [ ] **T-EN07.4** `INF` — **Stack giám sát**: OTel Collector → Tempo; Prometheus + Grafana (dashboard: độ trễ, lỗi, hàng đợi, circuit breaker, token); Loki
- [ ] **T-EN07.5** `INF` — **9 cảnh báo**: Theo SAD §4.3; probe ngoài mỗi phút trong 08:00–18:00 thứ Hai → thứ Sáu (LG-17)

## 5. Trường hợp biên và lưu ý

- Xem các trường hợp lỗi ở mục 3 (mã lỗi) và các tiêu chí nghiệm thu ở mục 6.

## 6. Tiêu chí nghiệm thu

- [ ] Một câu hỏi tạo trace đầu-cuối; test tự động xác nhận log không có trường nội dung

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Kiểm chứng tiêu chí hoàn thành ở mục 6 | Integration / báo cáo | EN-07 |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.
- [ ] 9 cảnh báo đã được kích hoạt thử ít nhất 1 lần trên staging (LG-17).

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
