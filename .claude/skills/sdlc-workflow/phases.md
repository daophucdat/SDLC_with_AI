# Các pha của workflow SDLC

Mỗi pha: **đầu vào → việc → artefact → xong khi**. Artefact nằm trong `docs/` (đã duyệt → baseline, AGENTS.md §5).
Skill dùng trong pha ở cột cuối của bảng tóm tắt.

| Pha | Tên | Artefact chính | Skill / công cụ |
|---|---|---|---|
| 0 | Khởi động | `docs/sdlc-state.md` | — |
| 1 | Phân tích | `docs/02-requirements/` (PRD, use case), `docs/implement/userStory.md` | — |
| 2 | Thiết kế | `docs/03-design/SAD.md`, `docs/04-design/`, `docs/adr/` | — |
| 3 | Lập kế hoạch | `docs/implement/dev_tasks.md`, `docs/implement/task/`, `docs/test-plan.md` | `/plan-tests` |
| 4 | Phát triển (mỗi story) | code + test + `docs/traceability.md` | `/plan-story` → `/gen-tests` → code → `/review-diff` → `/commit-gate` |
| 5 | Kiểm thử | `docs/test-cases.md`, `reports/test-report.md`, `docs/bugs.md` | `/plan-tests` → `/run-test-case` |
| 6 | Phát hành | `docs/release-<version>.md`, README, runbook | — |

## Pha 0 · Khởi động
- Đầu vào: đường dẫn BRD. Việc: đọc BRD, liệt kê mục tiêu, phạm vi, ràng buộc, các bên; tạo `docs/sdlc-state.md` (mẫu cuối file).
- Xong khi: state có mục tiêu, phạm vi trong / ngoài, câu hỏi mở về BRD.

## Pha 1 · Phân tích
- Việc: BRD → yêu cầu nghiệp vụ BR-xxx; use case; user story INVEST với AC Given / When / Then **có ngưỡng**; NFR có số (thời gian, dung lượng, tỉ lệ); edge case EC-xx; ưu tiên P0 / P1 / P2.
- Xong khi: mọi BR có ≥ 1 story; mọi story có AC đo được; NFR có số; không còn "nhanh", "thân thiện" không định lượng.

## Pha 2 · Thiết kế
- Việc: kiến trúc (lớp, luật import), hợp đồng API / SSE / mã lỗi, mô hình dữ liệu, luồng UI, bảo mật (threat model ngắn), quan sát (metric / log không chứa nội dung); mỗi lựa chọn có phương án thay thế → ADR.
- Xong khi: mọi story có đường đi qua kiến trúc; mọi API trong hợp đồng có mã lỗi; ADR cho mỗi quyết định khó đảo ngược.

## Pha 3 · Lập kế hoạch
- Việc: chia task theo story (≤ 1 ngày / task), thứ tự phụ thuộc, enabler (CI, hạ tầng); test plan 8 mục (mục tiêu, phạm vi, non-goals, chiến lược L0–L4, môi trường, rủi ro, tiêu chí thoát, artefact).
- Xong khi: backlog có thứ tự; mỗi task trỏ về story; cổng CI L0 định nghĩa xong.

## Pha 4 · Phát triển — lặp mỗi story
- Việc: `/plan-story` (dừng nếu AC mơ hồ) → `/gen-tests` (đỏ trước) → code nhỏ nhất cho xanh → `bash scripts/dev.sh check` → `/review-diff` (≥ 10/14) → trình cổng story → `/commit-gate`.
- Xong khi (mỗi story): 100% AC có test tự động; `dev.sh check` xanh; traceability cập nhật; rubric ≥ 10/14.

## Pha 5 · Kiểm thử
- Việc: `/plan-tests` cho story P0 → `/run-test-case all` **2 lượt**, retries 0 → `python scripts/test_report.py` → mỗi FAIL một phiếu (BUG / TD / HD) → BUG quay về pha 4.
- Xong khi: tiêu chí thoát của test plan đạt; không BUG mức cao mở; báo cáo có bằng chứng từng TC.

## Pha 6 · Phát hành
- Việc: release note (story đã xong, thay đổi API, việc vận hành, rủi ro còn lại, TC thủ công chưa chạy), cập nhật README / runbook, kiểm truy vết đầy đủ.
- Xong khi: `python scripts/check_traceability.py matrix` OK; release note được duyệt.

## Mẫu docs/sdlc-state.md

```markdown
# Trạng thái SDLC
Pha hiện tại: 4 · Phát triển — US-201 (đang chờ cổng)
BRD: docs/02-requirements/BRD.md

| Ngày | Pha | Quyết định của người duyệt | Ghi chú |
|---|---|---|---|
| 2026-10-20 | 1 | duyệt | 14 story, 3 câu hỏi đã trả lời |

Yêu cầu thay đổi đang mở: (không)
Câu hỏi mở: (không)
```
