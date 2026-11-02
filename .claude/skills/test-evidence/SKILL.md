---
name: test-evidence
description: >-
  Đóng gói bằng chứng kiểm thử có hình động: chạy test case Playwright có ghi video, dựng GIF từ trace cho
  từng TC, nhúng ảnh / GIF / video vào reports/test-report.md và thư viện reports/test-media.md. Dùng khi
  người dùng muốn báo cáo test có GIF hoặc video, quay lại màn hình một TC, demo kết quả test, gửi bằng chứng
  cho reviewer / PO.
argument-hint: "[TC-xxx-yy | US-xxx | all] [--no-run]"
disable-model-invocation: true
allowed-tools: Read Grep Glob Edit Bash(cd e2e*) Bash(npx playwright*) Bash(npm run*) Bash(PYTHONUTF8=1 *) Bash(du *) Bash(git status*) Bash(git diff*) mcp__chatdocs-sdlc__test_results mcp__chatdocs-sdlc__test_cases mcp__chatdocs-sdlc__defect
---

Bằng chứng cho **$ARGUMENTS** (Day 6, L4). Chỉ người gọi: skill khởi động server và ghi `reports/`.

## KHÔNG ĐƯỢC
- **Không sửa test, kỳ vọng hay ngưỡng** để có video "đẹp". GIF / video là bằng chứng của lượt chạy thật, kể cả lượt FAIL.
- Không cắt / chỉnh GIF bằng tay, không ghép khung từ lượt khác. Muốn khác thì đổi hằng số trong `scripts/test_media.py` và chạy lại.
- Không bật `retries`, không dừng tiến trình không do skill này khởi động (cổng bận → `E2E_WEB_PORT` / `E2E_API_PORT`).
- Không sửa `backend/`, `web/` trong lúc test đang chạy.
- Không commit video khi tổng `reports/videos/` > 30 MB — chỉ giữ GIF + ảnh, video để trong artefact CI.

## Công cụ
- `e2e/playwright.config.ts`: `video` bật mặc định (1280×800); `E2E_VIDEO=off` để tắt. Trace luôn bật — GIF dựng từ screencast trong trace.
- `scripts/test_media.py [run…]`: copy video → `reports/videos/<run>/<TC>.webm`, dựng `reports/gifs/<run>/<TC>.gif` (Pillow, ≤ 8 khung/s, khoảng lặng rút còn 2 s), viết `reports/test-media.md`. Test chung nhiều TC → tên `TC-303-01+TC-303-10`.
- `scripts/test_report.py`: cột bằng chứng của `reports/test-report.md` link ảnh + GIF + video.
- MCP `chatdocs-sdlc` (`.mcp.json`): `test_results` (kết quả + link bằng chứng), `test_cases` (kỳ vọng), `defect` (phiếu lỗi).

## Quy trình
1. Đọc kỳ vọng của từng TC (`test_cases` hoặc `docs/test-cases.md`) — cột PASS khi / FAIL khi là chuẩn.
2. Chạy (bỏ qua nếu `--no-run` và đã có `reports/results-<run>.json` + video trong `e2e/test-results/`):
   - một / vài TC: `cd e2e && E2E_RUN=<run> npx playwright test -g "TC-201-05|TC-201-06"`;
   - cả bộ, 2 lượt: `E2E_RUN=run1 npm run test:tc` rồi `E2E_RUN=run2 npx playwright test`.
3. `PYTHONUTF8=1 backend/.venv/Scripts/python.exe scripts/test_media.py` rồi `… scripts/test_report.py`
   (Linux / CI: `python`). Pillow nằm trong extra `dev` của backend.
4. Mở 2–3 GIF (đọc khung cuối bằng Read) — khung cuối phải cho thấy đúng điều TC khẳng định; nếu không, ghi lại, không che.
5. `du -sh reports/gifs reports/videos`; áp luật 30 MB ở trên.
6. Báo cáo: số TC PASS / FAIL mỗi lượt, đường dẫn `reports/test-media.md`, FAIL nào → phiếu nào (`defect`). FAIL mới → mở phiếu qua `/run-test-case`, không sửa ở đây.
