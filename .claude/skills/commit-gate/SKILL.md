---
name: commit-gate
description: >-
  Cổng trước khi commit: chạy toàn bộ cổng L0 (lint, typecheck, coverage, traceability) trên đúng phần đã stage,
  kiểm tra commit message Conventional Commits + mã US/EN, ghi reports/gate-<tree>.json, chỉ commit khi PASS.
  Dùng khi người dùng muốn commit, chốt thay đổi, kiểm tra trước khi commit hay "qua cổng".
argument-hint: '"type(scope): tóm tắt [US-xxx]"'
disable-model-invocation: true
allowed-tools: Read Grep Bash(git status*) Bash(git diff*) Bash(git add *) Bash(git commit *) Bash(git log*) Bash(git rev-parse*) Bash(python .claude/skills/commit-gate/scripts/gate.py*) Bash(backend/.venv/Scripts/python.exe .claude/skills/commit-gate/scripts/gate.py*)
---

Commit có cổng cho: **$ARGUMENTS**. Chỉ người gọi — commit là tác dụng phụ.

## KHÔNG ĐƯỢC
- Không commit khi `reports/gate-*.json` của đúng tree đó chưa `"ok": true`.
- Không `--no-verify`, không `git push`, không `--amend` commit đã có, không sửa ngưỡng cổng để qua.
- Không `git add -A` / `git add .`: stage từng file liên quan; không stage `.env`, `reports/gate-*`, `e2e/test-results/`, file `*.py.bak`.
- Gate FAIL → dừng, báo lỗi nguyên văn; không tự sửa rồi commit trong cùng lượt.

## Ngữ cảnh
- Đang stage: !`git diff --cached --stat`
- Chưa stage: !`git status --short`

## Quy trình
1. Xem `git status` và `git diff`. Stage đúng các file của một thay đổi logic (commit nhỏ). Có file của thay đổi khác → hỏi.
2. Message: Conventional Commits + mã yêu cầu, thân ghi **vì sao** (AGENTS.md §8). Thiếu mã → đề xuất, không bịa mã.
3. Chạy `python .claude/skills/commit-gate/scripts/gate.py "<message>"` (Windows: `backend/.venv/Scripts/python.exe …`). Mất vài phút.
4. PASS → `git commit` với đúng message; báo `HEAD`, đường dẫn file gate và thời gian từng cổng. FAIL → bảng cổng FAIL + 15 dòng log cuối, dừng.
5. Kiểm: `git rev-parse HEAD^{tree}` khớp `tree` trong file gate.
