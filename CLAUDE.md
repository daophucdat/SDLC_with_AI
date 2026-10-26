# CLAUDE.md

Quy tắc làm việc của agent trong repo này nằm ở **[AGENTS.md](AGENTS.md)** — đọc file đó trước khi sửa code.

Tóm tắt bắt buộc:
- Nguồn sự thật là `docs/`; AC chưa rõ thì hỏi, không đoán. Không sửa đặc tả đã baseline (AGENTS.md §5).
- Vòng lặp mỗi story: `/plan-story` → `/gen-tests` → code → `make check` → `/review-diff` → `/fix-ci` khi CI đỏ.
- Commit: Conventional Commits + mã `US-xxx` / `EN-xx` / `REL-xx` / `BR-xxx`; cập nhật `docs/traceability.md` cùng commit.
- Không sửa test cho pass; không nới cổng chất lượng.
