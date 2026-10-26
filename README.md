# Chat với tài liệu (MVP)

Đội BD tải PDF lên kho chung và hỏi đáp bằng AI; mỗi ý trong câu trả lời có trích dẫn tài liệu và trang.

1. **Cài:** Docker Desktop (đủ để chạy) · thêm Python 3.12 + Node 20 nếu muốn phát triển → `make install`
2. **Cấu hình:** không cần cho dev (LLM giả lập, Keycloak có sẵn tài khoản). Dùng Claude thật: `export LLM_PROVIDER=anthropic LLM_API_KEY=…`
3. **Chạy:** `make up` → mở http://localhost:5173, đăng nhập `thu.ha` / `Test@1234` (Trưởng nhóm: `quoc.bao`)
4. **Test:** `make test` (backend + web) · toàn bộ cổng chất lượng: `make check`
5. **Dừng:** `make down`

Không có `make` (Windows): dùng `bash scripts/dev.sh <lệnh>` với cùng tên lệnh, ví dụ `bash scripts/dev.sh up`.

| Đọc tiếp | |
|---|---|
| Quy tắc làm việc (người và agent) | [AGENTS.md](AGENTS.md) |
| Yêu cầu, thiết kế | [docs/02-requirements](docs/02-requirements), [docs/03-design/SAD.md](docs/03-design/SAD.md) |
| Truy vết US ↔ code ↔ test | [docs/traceability.md](docs/traceability.md) |
| Quyết định kiến trúc khi hiện thực | [docs/adr](docs/adr/README.md) |
| Chất lượng: rubric review, lỗi lọt | [docs/quality](docs/quality) |
| Vận hành, ra mắt | [docs/implement/reports](docs/implement/reports/README.md) |
