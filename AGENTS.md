# AGENTS.md — hướng dẫn cho agent (và người) làm việc trong repo này

Agent là một thành viên của đội: làm theo đúng quy trình, để lại bằng chứng, không tự nới tiêu chuẩn. Đọc hết file này trước khi sửa code.

## 1. Dự án

MVP **"Chat với tài liệu"**: đội BD tải PDF lên kho chung và hỏi đáp bằng AI; mỗi ý có trích dẫn tài liệu + trang.

| Nguồn sự thật | Ở đâu |
|---|---|
| Yêu cầu, story, AC | `docs/02-requirements/` (BRD, PRD, use case), `docs/implement/userStory.md` |
| Kiến trúc, thiết kế | `docs/03-design/SAD.md`, `docs/04-design/` |
| Hợp đồng API / CSDL / SSE / mã lỗi | `docs/implement/dev_tasks.md` Phần 0 |
| Task đang làm | `docs/implement/task/*.md` |
| Quyết định phát sinh khi code | `docs/adr/` |
| Truy vết US ↔ BR ↔ code ↔ test | `docs/traceability.md` |

**AC chưa rõ thì dừng lại và hỏi, không đoán.** Mọi câu hỏi phạm vi quay về tài liệu, không quay về trí nhớ.

## 2. Stack

- **backend/** — Python 3.12 (chạy được 3.10), FastAPI, Pydantic v2, SQLAlchemy 2 async + asyncpg, Alembic, PostgreSQL 16 + pgvector, MinIO/S3, Hugging Face TEI (BGE-M3), Claude API (`anthropic`).
  Kiến trúc lớp: `domain` → `ports` → `application` → `adapters` (+ `platform`). Luật import kiểm bằng import-linter.
- **web/** — React 18, TypeScript strict, Vite 4, TanStack Query 5, Zustand, PDF.js.
- **infra/** — docker compose (dev), Keycloak, nginx, Prometheus/Grafana/Tempo/Loki, script sao lưu.
- **eval/**, **e2e/** — harness đánh giá chất lượng, Playwright / axe / k6.

## 3. Lệnh

```bash
make up            # toàn bộ hệ thống (docker compose) — http://localhost:5173, user thu.ha / Test@1234
make install       # cài backend (.venv) + web (node_modules)
make check         # = mọi cổng L0 chạy được trên máy: lint, type, complexity, import rules, test + coverage, traceability
make test          # chỉ test backend + web
make mutation      # mutation score module lõi (chậm, CI chạy hằng tuần)
```

> `make mutation` (mutmut) **sửa file nguồn tại chỗ** trong lúc chạy: không chạy test, commit hay agent khác trên cùng thư mục cho tới khi nó xong (kiểm tra `git status` sạch, không còn file `*.py.bak`).

Không có `make` (Windows): `bash scripts/dev.sh <lệnh>` — cùng tên lệnh.

## 4. Quy ước code

- Đọc file xung quanh trước khi viết: cùng mật độ comment, cách đặt tên, idiom. Comment giải thích **vì sao**, kèm mã yêu cầu (`US-301`, `AC-303.3`, `SEC-06`…).
- `domain` không import gì ngoài stdlib; SDK bên ngoài chỉ ở `adapters/*`. Mọi tham số cấu hình nằm trong `platform/config.py`.
- Thông điệp cho người dùng chỉ ở `web/src/i18n/vi.ts`; backend chỉ trả `code` (RFC 9457 problem+json).
- Không bao giờ ghi nội dung tài liệu / câu hỏi / câu trả lời vào log, metric, span hay sự kiện phân tích (TC-08).
- Độ phức tạp mỗi hàm ≤ 10; không thêm `# noqa` / `eslint-disable` để qua cổng mà không ghi lý do ngay cạnh đó.
- Test viết theo **AC**, không theo code: tên test nêu AC (`… (AC-304.4)`). Mock ở biên (port), không mock domain.

## 5. Điều cấm

1. **Không sửa đặc tả đã baseline** để test xanh: `docs/02-requirements/`, `docs/03-design/`, `docs/04-design/`, `docs/05-review/`, `docx/`, `docs/implement/dev_tasks.md`, `docs/implement/userStory.md`. Muốn đổi → đó là thay đổi yêu cầu: mở issue, qua review như một thay đổi phạm vi. (`.claude/settings.json` chặn các đường dẫn này.)
2. **Không sửa test cho pass** thay vì sửa code (đổi assertion, `expect(true)`, `skip`, nới ngưỡng). Test sai thật → giải thích trong PR, reviewer đồng ý.
3. Không hạ ngưỡng cổng chất lượng (coverage, complexity, audit) trong cùng PR với code bị chặn.
4. Không commit secret, `.env`, dữ liệu thật của khách hàng; không gửi tài liệu ra dịch vụ ngoài ngoài LLM đã được cấu hình.
5. Không `git push --force`, không sửa lịch sử `main`, không tự merge.

## 6. Quyền hạn của agent

| Được | Không được |
|---|---|
| Sửa `backend/`, `web/`, `e2e/`, `eval/`, `infra/`, `scripts/` | Sửa đặc tả baseline (mục 5.1) |
| Thêm / sửa test, `docs/traceability.md`, `docs/adr/`, `docs/quality/`, `docs/implement/reports/`, trạng thái trong `docs/implement/task/README.md` | Approve hay merge PR (L1 chỉ là tư vấn) |
| Chạy lệnh trong `Makefile`, đọc log CI | Tắt / nới cổng CI |

## 7. Vòng lặp cho mỗi user story (Specify → Generate → Verify → Refine)

Các bước là skill trong `.claude/skills/` (danh mục: `docs/skills.md`); kiểm thử theo test case: `/plan-tests`, `/run-test-case` (Day 6).

1. **Plan** — `/plan-story US-xxx`: đọc story, AC, task; liệt kê AC → test sẽ viết, file sẽ đổi, câu hỏi còn mở. Dừng nếu AC chưa rõ.
2. **Test trước** — `/gen-tests US-xxx`: viết test theo từng AC (cả edge case và trường hợp âm), chạy để thấy chúng **đỏ**.
3. **Code** — thay đổi nhỏ nhất để test xanh; giữ ranh giới lớp.
4. **Verify** — `make check`; rồi `/review-diff` (L1, rubric `docs/quality/code_review_rubric.md`).
5. **Refine** — sửa theo bằng chứng (log, comment), không theo cảm giác. `/fix-ci` khi CI đỏ.
6. **Ghi lại** — cập nhật `docs/traceability.md`; quyết định kiến trúc mới → ADR trong `docs/adr/`.
7. **Commit** — `/commit-gate "type(scope): … [US-xxx]"`: chạy cổng L0 trên phần đã stage, ghi `reports/gate-<tree>.json`, chỉ commit khi PASS.

Dừng khi mọi cổng xanh và Definition of Done (mục 9) đạt.

## 8. Commit và PR

- Commit nhỏ, **Conventional Commits** và có mã yêu cầu: `feat(qa): giữ 16 ký tự đầu của câu trả lời [US-304]`. Hook `commit-msg` (`.githooks/`) chặn ngay trên máy, CI chặn lần nữa (`scripts/check_traceability.py`).
- PR ≤ ~400 dòng thay đổi; dùng mẫu `.github/pull_request_template.md`; 1 approver không phải người viết code (L2, `CODEOWNERS`).

## 9. Definition of Done

- Chạy được bằng 1 lệnh (`make up`); README có cài, cấu hình, chạy, test.
- 100% AC của story có test tự động; coverage ≥ 70% (lõi ≥ 90%).
- CI xanh: lint, type, complexity, import rules, test, build, secret scan, dependency scan, traceability.
- Review L2: 1 approver khác người viết, checklist PR đã tick, rubric ≥ 10/14 và không mục nào 0 điểm.
- `docs/traceability.md` cập nhật: US ↔ BR ↔ code ↔ test.
