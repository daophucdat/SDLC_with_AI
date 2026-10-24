# US-402 · Chạy bộ câu hỏi kiểm thử và xuất kết quả

| Thuộc tính | Giá trị |
|---|---|
| Loại | User story · E4. Đo lường giá trị |
| Sprint | Sprint 4 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | P2 |
| Story point | 5 `[Đề xuất]` |
| Vai trò thực hiện | Backend, Frontend |
| Phụ thuộc | EN-10 (harness đánh giá) |
| Chặn bởi | — |
| Feature flag | `evaluation` |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

> Là **trưởng nhóm BD**, tôi muốn chạy bộ câu hỏi kiểm thử và xuất kết quả ra bảng tính để chấm, để có số liệu M-002 khi nghiệm thu.

**Truy vết:** UC-05 · UCD-27, UCD-28 · DEP-003 · M-002

**Thiết kế giao diện:** [`metrics.html (tab Nghiệm thu)`](../../04-design/UI_UX_design/metrics.html)

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** Những gì không được liệt kê ở mục 4 và mục 6.

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

**API**

| # | Endpoint | Request | Response 2xx | Lỗi (code) | Story |
|---|---|---|---|---|---|
| V1 | `POST /api/v1/evaluations` | multipart `.xlsx` | 202 `{runId, total}` | 400 TESTSET_INVALID `{row, column}` | US-402 |
| V2 | `GET /api/v1/evaluations/{runId}` | — | `{status, done, total}` | — | US-402 |
| V3 | `GET /api/v1/evaluations/{runId}/export` | — | 200 `.xlsx` | 409 (chưa xong) | US-402 |

**Mã lỗi**

| code | HTTP | Thông điệp FE (`vi.ts`) | Hành động FE |
|---|---|---|---|
| TESTSET_INVALID | 400 | "Dòng {row}: thiếu cột {column}." | Hiển thị dưới ô chọn file |

## 4. Công việc chi tiết

- [ ] `BE` V1 → V3; đọc .xlsx bằng `openpyxl` và kiểm tra cột (`TESTSET_INVALID {row, column}`); job `run_evaluation` gọi trực tiếp `QuestionAnsweringService` (không qua HTTP), timeout 60 phút; xuất .xlsx.
- [ ] `FE` `EvaluationTab` theo `metrics.html` (tải file, thanh tiến độ, bảng kết quả, tải về)

## 5. Trường hợp biên và lưu ý

- Xem các trường hợp lỗi ở mục 3 (mã lỗi) và các tiêu chí nghiệm thu ở mục 6.

## 6. Tiêu chí nghiệm thu

- [ ] **AC-402.1** — *Given* một file .xlsx đúng mẫu (≤ 200 dòng), *When* tôi chạy, *Then* tôi thấy tiến độ và nhận file kết quả gồm câu hỏi, câu trả lời, trích dẫn, cột để chấm.
- [ ] **AC-402.2** — *Given* file sai mẫu, *When* tôi tải lên, *Then* hệ thống nêu đúng dòng và cột bị lỗi.
- [ ] **AC-402.3** — *Given* lần chạy quá 60 phút, *When* hết giờ, *Then* hệ thống dừng và giữ kết quả đã có.

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Kiểm chứng AC-402.1 như mô tả ở mục 6 | Integration | AC-402.1 |
| Kiểm chứng AC-402.2 như mô tả ở mục 6 | Integration | AC-402.2 |
| Kiểm chứng AC-402.3 như mô tả ở mục 6 | Integration | AC-402.3 |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
