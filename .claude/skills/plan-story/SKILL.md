---
name: plan-story
description: >-
  Lập kế hoạch hiện thực một user story (US-xxx) trước khi code: đọc story, AC, task, hợp đồng API; ra bảng
  AC → test, file sẽ đổi theo lớp, rủi ro, ADR, câu hỏi mở; dừng nếu AC chưa rõ. Dùng khi người dùng muốn bắt đầu
  story, lên kế hoạch, ước lượng, "làm US-xxx thế nào", "cần sửa file nào".
argument-hint: US-xxx
allowed-tools: Read Grep Glob Bash(git log*) Bash(git diff*)
disallowed-tools: Edit Write NotebookEdit
---

Lập kế hoạch cho **$ARGUMENTS** (AGENTS.md §7 bước 1 — Specify).

## KHÔNG ĐƯỢC
- **Không sửa file nào** trong skill này (chỉ đọc và trả kế hoạch).
- Không đoán AC: AC mơ hồ, mâu thuẫn, thiếu ngưỡng → "Câu hỏi mở" và kết luận "CHƯA BẮT ĐẦU ĐƯỢC".
- Không đề xuất đổi đặc tả baseline để dễ hiện thực.

## Quy trình
1. Đọc story và AC trong `docs/implement/userStory.md`, task `docs/implement/task/$ARGUMENTS-*.md`, hợp đồng liên quan trong `docs/implement/dev_tasks.md` Phần 0, dòng của story trong `docs/traceability.md`.
2. Kiểm tra từng AC đo được không (Given / When / Then cụ thể, có ngưỡng).
3. Đọc code hiện có liên quan (theo `docs/traceability.md` và tìm kiếm) để biết phần nào đã có.
4. Trả về đúng các mục:
   - **AC → test**: `AC | loại test (unit / API / integration / E2E) | tên test dự kiến | biên và âm`.
   - **File sẽ đổi**: theo lớp (`domain`, `ports`, `application`, `adapters`, `web/src/...`), lý do từng file.
   - **Rủi ro**: an toàn (auth, dữ liệu, injection), hiệu năng (ngưỡng NFR), thay đổi hợp đồng API.
   - **ADR cần ghi?** có / không, vì sao.
   - **Câu hỏi mở**.
5. Ước lượng số dòng; > 400 dòng → chia nhiều PR, mỗi PR là một lát cắt dọc chạy được.
