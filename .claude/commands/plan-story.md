---
description: Lập kế hoạch cho một user story (Specify) — AC → test → file, dừng nếu AC chưa rõ
argument-hint: US-xxx
---

Lập kế hoạch cho **$ARGUMENTS** theo AGENTS.md §7 bước 1. **Chưa sửa file nào** trong lệnh này.

1. Đọc story và AC trong `docs/implement/userStory.md`, task `docs/implement/task/$ARGUMENTS-*.md`, các phần hợp đồng liên quan trong `docs/implement/dev_tasks.md` Phần 0, và dòng của story trong `docs/traceability.md`.
2. Kiểm tra từng AC có đo được không (Given / When / Then cụ thể, có ngưỡng). AC nào mơ hồ, mâu thuẫn với tài liệu khác, hoặc thiếu ngưỡng → liệt kê ở mục "Câu hỏi mở" và **dừng**, không đoán.
3. Đọc code hiện có liên quan (theo `docs/traceability.md` và tìm kiếm) để biết phần nào đã có.
4. Trả về đúng các mục sau:
   - **AC → test**: bảng `AC | loại test (unit / API / integration / E2E) | tên test dự kiến | trường hợp biên và âm`.
   - **File sẽ đổi**: theo lớp (`domain`, `ports`, `application`, `adapters`, `web/src/...`), lý do từng file.
   - **Rủi ro**: an toàn (auth, dữ liệu, injection), hiệu năng (ngưỡng NFR), thay đổi hợp đồng API.
   - **ADR cần ghi?**: có / không, vì sao.
   - **Câu hỏi mở**: nếu có thì kết luận "CHƯA BẮT ĐẦU ĐƯỢC".
5. Ước lượng số dòng thay đổi; nếu > 400 dòng, đề xuất cách chia thành nhiều PR (mỗi PR là một lát cắt dọc chạy được).
