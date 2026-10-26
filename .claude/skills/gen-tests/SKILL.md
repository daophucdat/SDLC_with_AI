---
name: gen-tests
description: >-
  Viết code test tự động (pytest, Vitest) theo từng AC của một user story trước khi viết code — test phải đỏ
  trước. Dùng khi người dùng muốn viết test, thêm unit test / API test, TDD, "test trước", phủ AC bằng test
  tự động, hoặc tái hiện một BUG bằng test.
argument-hint: US-xxx | BUG-xx
allowed-tools: Read Grep Glob Edit Write Bash(cd backend*) Bash(cd web*) Bash(backend/.venv/Scripts/python.exe -m pytest*) Bash(npx vitest*)
---

Viết test tự động cho **$ARGUMENTS** (AGENTS.md §7 bước 2).

## KHÔNG ĐƯỢC
- Không đọc phần hiện thực để "đoán" kết quả mong đợi — lấy từ AC và hợp đồng `docs/implement/dev_tasks.md` §0.
- Không mock thứ đang được kiểm tra; chỉ mock ở biên (port: LLM, storage, IdP, embedder).
- Không viết code sản phẩm trong skill này; không `skip` / `xfail` để xanh.

## Quy tắc
- Mỗi AC có **≥ 1** test; tên test kết thúc bằng mã AC: `test_no_chunks_is_not_found_without_calling_the_llm (AC-304.4)` / `it("… (AC-304.4)")`.
- Mỗi AC có thêm trường hợp **biên** và **âm** (rỗng / quá giới hạn, không có quyền, lỗi phụ thuộc).
- Backend: unit cho `domain` (không mock), API qua `httpx.ASGITransport` với fake trong `backend/tests/fakes.py`, tích hợp PostgreSQL trong `backend/tests/integration/` (đánh dấu `integration`). Frontend: Vitest + Testing Library, truy vấn theo vai trò / nhãn, axe với màn hình mới.

## Sau khi viết
1. Chạy (`cd backend && .venv/Scripts/python -m pytest -q <file>` · `cd web && npx vitest run <file>`). Test cho phần chưa có **phải đỏ**; xanh ngay → test không kiểm tra gì, sửa test.
2. Cập nhật cột test của story trong `docs/traceability.md`.
3. Báo cáo: `AC | test | đỏ/xanh | lý do`.
