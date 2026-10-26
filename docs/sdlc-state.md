# Trạng thái SDLC

Sổ trạng thái của skill `/sdlc-workflow` (`.claude/skills/sdlc-workflow/`): pha hiện tại, quyết định của người duyệt, yêu cầu thay đổi. Phiên sau đọc file này để chạy tiếp.

Pha hiện tại: **6 · Phát hành — chưa bắt đầu** (pha 5 đã xong cho US-201, US-303; các story P0 khác còn TC chưa viết)
BRD: `docs/02-requirements/BRD.md`

| Ngày | Pha | Quyết định của người duyệt | Artefact / ghi chú |
|---|---|---|---|
| 2026-10-19 | 1 · Phân tích | duyệt | `docs/02-requirements/` (BRD, PRD, use case), `docs/implement/userStory.md` |
| 2026-10-19 | 2 · Thiết kế | duyệt | `docs/03-design/SAD.md`, `docs/04-design/`, review `docs/05-review/` |
| 2026-10-19 | 3 · Lập kế hoạch | duyệt | `docs/implement/dev_tasks.md`, `docs/implement/task/` (37 task) |
| 2026-10-24 | 4 · Phát triển | duyệt ("push thẳng lên main, dự án học, không cần review PR") | 37 task, Sprint 0 → 5 |
| 2026-10-26 | 4 · Chất lượng (Day 5) | duyệt | cổng L0, rubric L1, mutation 94,7 %, `docs/traceability.md` |
| 2026-10-26 | 5 · Kiểm thử (Day 6) | chờ duyệt | `docs/test-plan.md`, `docs/test-cases.md`, `reports/test-report.md` (22/22 TC × 2 lượt), `docs/bugs.md` |

Yêu cầu thay đổi đang mở: (không)

Câu hỏi mở:
- OBS-1 (`docs/bugs.md`): hành vi mong muốn khi mất kết nối *sau* khi server đã lưu file — cần PO quyết định trước khi viết TC-201-14.
- TC-303-05 cần staging + LLM thật.
