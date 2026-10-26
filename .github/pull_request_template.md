## Story / yêu cầu

<!-- US-xxx / EN-xx / REL-xx — đường dẫn tới docs/implement/task/... -->

## AC → test

| AC | Test chứng minh | Loại (unit / API / integration / E2E) |
|---|---|---|
| AC-… | `…` | |

## Thay đổi

<!-- Vì sao (không cần kể lại diff). Quyết định kiến trúc mới → ADR trong docs/adr/. Thay đổi hợp đồng API → nêu rõ. -->

## Checklist người viết

- [ ] Mỗi AC của story có test tự động; có trường hợp biên và âm
- [ ] Không sửa đặc tả baseline, không nới test / ngưỡng để xanh (AGENTS.md §5)
- [ ] `make check` xanh trên máy; CI xanh (lint, type, complexity, test + coverage, build, secret, dependency, traceability)
- [ ] Commit theo Conventional Commits và có mã US/EN/REL/BR
- [ ] `docs/traceability.md` cập nhật; ADR nếu có quyết định kiến trúc mới
- [ ] Không có nội dung tài liệu / câu hỏi trong log, metric, span, sự kiện
- [ ] Diff ≤ ~400 dòng (hoặc giải thích vì sao không chia được)

## Review L1 (agent, tư vấn) — kết quả `/review-diff`

<!-- dán bảng điểm rubric + comment blocker/major -->

## Review L2 (người, bắt buộc) — docs/quality/code_review_rubric.md

| Tiêu chí | Điểm 0–2 | Bằng chứng |
|---|---|---|
| Đúng AC | | |
| Test | | |
| Thiết kế | | |
| An toàn | | |
| Hiệu năng | | |
| Dễ đọc | | |
| Truy vết | | |
| **Tổng (≥ 10/14, không mục nào 0)** | | |
