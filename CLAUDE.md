# CLAUDE.md

@AGENTS.md

Phần dưới chỉ là sự thật riêng cho Claude Code. Quy trình nhiều bước nằm trong skill (`.claude/skills/`), luật cứng nằm trong hook / CI — không chép lại ở đây. File này + AGENTS.md < 200 dòng (`python scripts/check_skills.py` kiểm).

## Skill của repo (danh mục, chủ sở hữu, version: docs/skills.md)

| Skill | Ai gọi | Dùng khi |
|---|---|---|
| `/plan-story US-xxx` | bạn hoặc Claude | trước khi code một story |
| `/gen-tests US-xxx` | bạn hoặc Claude | viết test theo AC, đỏ trước |
| `/review-diff [range]` | bạn hoặc Claude | review L1 theo rubric |
| `/plan-tests US-xxx` | bạn hoặc Claude | AC → test case trong `docs/test-cases.md` |
| `/run-test-case TC-…` | chỉ bạn | chạy TC Playwright, lưu bằng chứng |
| `/commit-gate "msg"` | chỉ bạn | cổng L0 → `reports/gate-<tree>.json` → commit |
| `/fix-ci [run]` | chỉ bạn | CI đỏ |
| `/sdlc-workflow <BRD>` | chỉ bạn | cả vòng SDLC, cổng duyệt mỗi pha, trạng thái `docs/sdlc-state.md` |

## Kiểm thử (Day 6)

- Test case + kỳ vọng ghi trước: `docs/test-cases.md`; kế hoạch: `docs/test-plan.md`; phiếu lỗi: `docs/bugs.md`.
- App test cục bộ, không cần Docker: `backend/tests/e2e_server.py` (API :8000) + Vite :5180 — Playwright tự khởi động cả hai.
- Chạy: `cd e2e && E2E_RUN=run1 npm run test:tc` (tạo fixture rồi chạy 22 TC), lượt 2 `E2E_RUN=run2`; một TC: `npx playwright test -g "TC-201-05"`.
- Báo cáo: `python scripts/test_report.py` → `reports/test-report.md`; ảnh `reports/screenshots/<run>/<TC>.png`; trace `e2e/test-results/`.
- `retries: 0`. FAIL → tìm nguyên nhân có bằng chứng rồi phân loại BUG / TD / HD; **không** đổi kỳ vọng cho khớp kết quả.
- Đang chạy test: không sửa `backend/`, `web/` cùng lúc (server dev nạp lại giữa chừng); không dừng tiến trình không do mình khởi động — cổng bị chiếm thì đặt `E2E_WEB_PORT` / `E2E_API_PORT`.
- Stack đầy đủ (Keycloak, PostgreSQL, MinIO): `E2E_STACK=compose npx playwright test` sau `make up`.

## Gotcha đã gặp (Windows + Git Bash)

- Không có `make` → `bash scripts/dev.sh <lệnh>`. Python của dự án: `backend/.venv/Scripts/python.exe`.
- Python in tiếng Việt ra console → đặt `PYTHONUTF8=1` (mặc định cp1252 làm vỡ `print`).
- Heredoc trong Bash làm hỏng `\n`, `\b` và dấu nháy khi ghi code → dùng Edit / Write, không `cat <<EOF` cho file nguồn.
- `make mutation` / mutmut sửa file nguồn tại chỗ: không chạy test hay commit song song; cần `PYTHONUTF8=1` và `--runner` trỏ venv.
- Throttle mạng của DevTools chỉ giả lập upload (byte vẫn tới server) — muốn "mất mạng trước khi server nhận file" dùng `dropUploads()` (`e2e/specs/tc-helpers.ts`).
- Hook `commit-msg` (`.githooks/`, bật bằng `git config core.hooksPath .githooks`) chặn commit thiếu mã US/EN/REL/BR.

## Bộ nhớ

- `CLAUDE.local.md` (đã `.gitignore`): URL sandbox, dữ liệu test, ghi chú riêng của bạn.
- Auto memory chỉ giữ bài học ngắn và sở thích; quy trình → skill, sự thật dùng chung → file này.
