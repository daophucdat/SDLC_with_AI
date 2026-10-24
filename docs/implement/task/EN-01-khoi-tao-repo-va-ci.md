# EN-01 · Khởi tạo repo và CI

| Thuộc tính | Giá trị |
|---|---|
| Loại | Enabler · EN. Enabler kỹ thuật |
| Sprint | Sprint 0 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | Enabler (bắt buộc cho các story phụ thuộc) |
| Story point | 3 `[Đề xuất]` |
| Vai trò thực hiện | Backend, DevOps, QA |
| Phụ thuộc | — |
| Chặn bởi | — |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

Cấu trúc repo theo Blueprint §3.1; lint, format, import-linter (DR-1 → DR-5), test chạy trong CI

**Truy vết:** SAD ADR-01, Blueprint §3.3, QAS-09

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** Những gì không được liệt kê ở mục 4 và mục 6.

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

Task này không đổi hợp đồng chung; dùng quy ước ở dev_tasks.md §0.1.

## 4. Công việc chi tiết

- [ ] **T-EN01.1** `INF` — **Tạo cấu trúc repo**: Theo [implement_plan.md §6](implement_plan.md); `backend/pyproject.toml` (uv hoặc poetry), `web/package.json`
- [ ] **T-EN01.2** `INF` — **Pipeline CI**: GitHub Actions: `lint` (ruff, black --check, eslint, tsc) → `import-rules` → `test-be` (pytest) → `test-fe` (vitest) → `build`
- [ ] **T-EN01.3** `INF` — **Quy tắc import**: `.importlinter` với 5 contract DR-1 → DR-5; eslint-plugin-boundaries cho `web/src/*` (feature không import feature khác)
- [ ] **T-EN01.4** `BE` — **Khung app**: `backend/adapters/http/main.py` (FastAPI app, `/healthz`), `backend/platform/config.py` (§0.2), `backend/platform/logging.py` (structlog JSON)
- [ ] **T-EN01.5** `QA` — **Khung test**: `conftest.py` có fixture PostgreSQL qua testcontainers (image `pgvector/pgvector:pg16`); test mẫu cho domain

## 5. Trường hợp biên và lưu ý

- Xem các trường hợp lỗi ở mục 3 (mã lỗi) và các tiêu chí nghiệm thu ở mục 6.

## 6. Tiêu chí nghiệm thu

- [ ] Pull request đầu tiên chạy CI xanh; vi phạm quy tắc import làm CI đỏ

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Kiểm chứng tiêu chí hoàn thành ở mục 6 | Integration / báo cáo | EN-01 |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
