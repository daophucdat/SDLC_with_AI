# EN-12 · Bộ test E2E và test hiệu năng

| Thuộc tính | Giá trị |
|---|---|
| Loại | Enabler · EN. Enabler kỹ thuật |
| Sprint | Sprint 4 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | Enabler (bắt buộc cho các story phụ thuộc) |
| Story point | 5 `[Đề xuất]` |
| Vai trò thực hiện | QA |
| Phụ thuộc | Các story P0 / P1 cần kiểm thử |
| Chặn bởi | — |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

E2E cho F1 → F6; test 100 câu hỏi đo p95; kiểm tra truy cập trái phép; axe

**Truy vết:** LG-01, LG-06, LG-08, LG-10, LG-13, LG-14

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** Những gì không được liệt kê ở mục 4 và mục 6.

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

Task này không đổi hợp đồng chung; dùng quy ước ở dev_tasks.md §0.1.

## 4. Công việc chi tiết

- [ ] **T-EN12.1** `QA` — **E2E F1 → F6**: `e2e/specs/*.spec.ts` (Playwright, Keycloak thử, fake LLM trên dev / CI, LLM thật trên staging); mỗi AC P0 / P1 có ít nhất 1 test (LG-13)
- [ ] **T-EN12.2** `QA` — **Hiệu năng**: `e2e/perf/ask.js` (k6): 100 câu hỏi, 10 VU, đo p95 tổng thời gian và phần đầu, tỉ lệ lỗi (LG-06)
- [ ] **T-EN12.3** `QA` — **Khả năng tiếp cận**: `@axe-core/playwright` trên `/`, `/metrics`, `/denied`, dialog, vùng nguồn
- [ ] **T-EN12.4** `QA` — **Trình duyệt**: Chạy E2E trên 2 phiên bản mới nhất của trình duyệt chuẩn công ty (PQ-004) (LG-14)
- [ ] **T-EN12.5** `QA` — **Màn hình chính ≤ 3 s**: Lighthouse CI trên staging (LG-08)

## 5. Trường hợp biên và lưu ý

- Xem các trường hợp lỗi ở mục 3 (mã lỗi) và các tiêu chí nghiệm thu ở mục 6.

## 6. Tiêu chí nghiệm thu

- [ ] Bộ test chạy trên staging; báo cáo p95 và tỉ lệ lỗi

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Kiểm chứng tiêu chí hoàn thành ở mục 6 | Integration / báo cáo | EN-12 |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.
- [ ] Báo cáo p95 trên 100 câu hỏi ≤ 30 s (LG-06); axe sạch; E2E chạy trên trình duyệt chuẩn (LG-14).

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
