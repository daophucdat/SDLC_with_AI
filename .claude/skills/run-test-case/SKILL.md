---
name: run-test-case
description: >-
  Chạy test case Playwright theo mã TC (TC-201-05, TC-303-*) trên app test cục bộ, so kết quả với kỳ vọng
  PASS / FAIL đã ghi trong docs/test-cases.md, lưu bằng chứng và viết reports/tc-<mã>.md; FAIL thì mở phiếu
  trong docs/bugs.md. Dùng khi người dùng muốn chạy test case, chạy lại TC lỗi, kiểm thử E2E, lấy bằng chứng.
argument-hint: TC-xxx-yy [TC-…] | US-xxx | all
disable-model-invocation: true
allowed-tools: Read Grep Glob Edit Write Bash(cd e2e*) Bash(npx playwright*) Bash(npm run*) Bash(python scripts/test_report.py*) Bash(git status*) Bash(git diff*)
---

Chạy **$ARGUMENTS** (Day 6, L4). Chỉ người gọi: skill khởi động server, ghi `reports/`.

## KHÔNG ĐƯỢC
- **Không sửa test hay kỳ vọng cho xanh.** FAIL → điều tra tới nguyên nhân có bằng chứng (ảnh, trace, timeline request) rồi phân loại BUG / TD / HD ([docs/bugs.md](../../../docs/bugs.md)).
- Không bật `retries`, không thêm `waitForTimeout` để che lỗi; không `test.skip` một TC đang FAIL.
- Không dừng (kill) tiến trình không do skill này khởi động; cổng bị chiếm → đặt `E2E_WEB_PORT` / `E2E_API_PORT` khác.
- Không sửa code sản phẩm trong skill này — BUG được sửa ở lượt sau, qua `/gen-tests` + `/commit-gate`.

## Cách chạy
- Một / vài TC: `cd e2e && E2E_RUN=<tên> npx playwright test -g "TC-201-05|TC-201-06"` (tên test chứa mã TC).
- Một story: `-g "TC-201-"`. Tất cả: `E2E_RUN=run1 npm run test:tc` rồi `E2E_RUN=run2 …` (Day 6: chạy 2 lượt).
- Lần đầu trên máy: `cd e2e && npm ci && npx playwright install chromium`; dữ liệu: `npm run fixtures`.
- Bằng chứng: `reports/screenshots/<run>/<TC>.png`, `reports/junit-<run>.xml`, trace trong `e2e/test-results/`.

## Quy trình
1. Đọc dòng của từng TC trong `docs/test-cases.md` — **cột PASS khi / FAIL khi là chuẩn**, không phải assertion trong spec.
2. Chạy. Với mỗi FAIL: mở ảnh `test-failed-1.png`, đọc lỗi nguyên văn; nếu chưa rõ, viết spec debug tạm in timeline (request, trạng thái server qua API) — xoá sau khi xong.
3. Kết luận từng FAIL: sản phẩm sai (**BUG** → phiếu + test tầng thấp nhất bắt được) · kỳ vọng / dữ liệu TC sai (**TD** → sửa TC + "Lịch sử sửa") · bộ chạy / môi trường sai (**HD**).
4. Viết `reports/tc-<mã hoặc story>.md`: bảng `TC | kỳ vọng | quan sát | PASS/FAIL | bằng chứng | phiếu`.
5. Chạy đủ bộ: `python scripts/test_report.py` cập nhật `reports/test-report.md`.
