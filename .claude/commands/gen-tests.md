---
description: Viết test theo AC trước khi viết code (test phải đỏ trước)
argument-hint: US-xxx
---

Viết test tự động cho **$ARGUMENTS** theo AGENTS.md §7 bước 2.

Quy tắc:
- Mỗi AC của story có **ít nhất một** test; tên test kết thúc bằng mã AC, ví dụ `test_no_chunks_is_not_found_without_calling_the_llm (AC-304.4)` hoặc `it("… (AC-304.4)")`.
- Mỗi AC có thêm trường hợp **biên** và **âm** (đầu vào rỗng / quá giới hạn, không có quyền, lỗi phụ thuộc).
- Test viết theo **AC**, không theo code hiện có. Không đọc phần hiện thực để "đoán" kết quả mong đợi — lấy kết quả từ AC và hợp đồng `docs/implement/dev_tasks.md` §0.
- Backend: unit test cho `domain` (không mock), API test qua `httpx.ASGITransport` với fake trong `backend/tests/fakes.py`, test tích hợp PostgreSQL trong `backend/tests/integration/` (đánh dấu `integration`). Frontend: Vitest + Testing Library, truy vấn theo vai trò / nhãn, kiểm tra axe với màn hình mới.
- Chỉ mock ở biên (port: LLM, storage, IdP, embedder). Không mock thứ đang được kiểm tra.

Sau khi viết:
1. Chạy test (`cd backend && .venv/Scripts/python -m pytest -q <file>` hoặc `cd web && npx vitest run <file>`). Test cho phần chưa hiện thực **phải đỏ**; nếu xanh ngay, test đó không kiểm tra gì — sửa test.
2. Cập nhật cột "Test (AC)" của story trong `docs/traceability.md`.
3. Báo cáo: bảng `AC | test | đỏ/xanh | lý do`.
