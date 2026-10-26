---
name: fix-ci
description: >-
  Sửa CI đỏ (GitHub Actions) bằng thay đổi nhỏ nhất theo bằng chứng trong log: lấy log job lỗi, tái hiện trên
  máy, phân loại nguyên nhân, sửa, chạy lại. Dùng khi CI fail, pipeline đỏ, job lỗi, build hỏng trên PR.
argument-hint: "[run id hoặc tên job]"
disable-model-invocation: true
allowed-tools: Read Grep Glob Edit Write Bash(gh run*) Bash(bash scripts/dev.sh*) Bash(git status*) Bash(git diff*)
---

CI đang đỏ (**$ARGUMENTS**). Chỉ người gọi — skill sửa code.

## KHÔNG ĐƯỢC
- Không hạ ngưỡng coverage / complexity / audit; không thêm `skip`, `# noqa`, `eslint-disable`, `|| true`, `retry`, `sleep` để xanh.
- Không sửa test khi code sai; không sửa đặc tả baseline.
- Không commit / push trong skill này — commit qua `/commit-gate`.

## Quy trình
1. Log: `gh run list --limit 5`, `gh run view <id> --log-failed`. Xác định **job và bước đầu tiên** thất bại; đọc lỗi nguyên văn.
2. Tái hiện bằng đúng lệnh của bước đó (`.github/workflows/ci.yml`, `scripts/dev.sh`). Không tái hiện được → ghi khác biệt môi trường (Python / Node, PostgreSQL, biến môi trường).
3. Phân loại: code sai · test sai · cấu hình / môi trường · phụ thuộc có lỗ hổng · flaky.
4. Sửa **thay đổi nhỏ nhất** đúng nguyên nhân: code sai → sửa code; test sai thật (AC nói khác) → sửa test, giải thích bằng AC; flaky → tìm nguyên nhân (thời gian, thứ tự, trạng thái chung).
5. Chạy lại bước đó cho tới khi xanh, rồi `bash scripts/dev.sh check`.
6. Báo cáo nguyên nhân gốc + message đề xuất `fix(ci): … [mã]`; lỗi đã lọt review → thêm dòng vào `docs/quality/escaped_defects.md`.
