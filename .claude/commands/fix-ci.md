---
description: Sửa CI đỏ bằng thay đổi nhỏ nhất theo bằng chứng (log), không nới cổng
argument-hint: "[run id hoặc tên job]"
---

CI đang đỏ ($ARGUMENTS). Sửa theo AGENTS.md §7 bước 5.

1. Lấy log: `gh run list --limit 5`, `gh run view <id> --log-failed`. Xác định **job và bước đầu tiên** thất bại; đọc thông báo lỗi nguyên văn.
2. Tái hiện trên máy bằng đúng lệnh của bước đó (xem `.github/workflows/ci.yml` và `Makefile`). Không tái hiện được → ghi rõ khác biệt môi trường (phiên bản Python / Node, PostgreSQL, biến môi trường).
3. Phân loại nguyên nhân: code sai · test sai · cấu hình / môi trường · phụ thuộc có lỗ hổng · không ổn định (flaky).
4. Sửa **thay đổi nhỏ nhất** đúng nguyên nhân:
   - code sai → sửa code, không động vào test;
   - test sai thật (AC nói khác) → sửa test và giải thích bằng AC trong commit;
   - flaky → tìm nguyên nhân (thời gian, thứ tự, trạng thái chung), không thêm `retry` / `sleep` che lỗi.
   **Cấm:** hạ ngưỡng coverage / complexity / audit, thêm `skip`, `# noqa`, `eslint-disable`, `|| true` để xanh.
5. Chạy lại bước đó trên máy cho tới khi xanh, rồi `make check`.
6. Commit `fix(ci): … [mã US/EN]` kèm một dòng nguyên nhân gốc; nếu lỗi đã lọt qua review, thêm một dòng vào `docs/quality/escaped_defects.md`.
