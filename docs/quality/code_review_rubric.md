# Rubric review code (L1 agent + L2 người — cùng một thước đo)

Nguồn: Day 5 — "Rubric review code (0–2 mỗi tiêu chí)". Dùng cho `/review-diff` (L1, tư vấn) và cho người duyệt PR (L2, bắt buộc).

| Tiêu chí | 0 | 1 | 2 | Câu hỏi khi review dự án này |
|---|---|---|---|---|
| **Đúng AC** | Thiếu / sai AC | Đủ AC, thiếu edge case | Đủ AC + edge + lỗi | Mỗi AC của story có hành vi tương ứng? Mã lỗi đúng `dev_tasks.md` §0.6? |
| **Test** | Không có / không chạy | Có, phủ happy path | Phủ AC + edge + âm | *Test này chứng minh AC nào?* Có test bị nới để xanh không? Mock đúng ở biên (port)? |
| **Thiết kế** | Trộn trách nhiệm | Tách module, còn phụ thuộc | Ranh giới rõ, dễ thay | Giữ lớp `domain → ports → application → adapters`? `lint-imports` xanh? Độ phức tạp ≤ 10? |
| **An toàn** | Lộ secret / injection | Có kiểm tra cơ bản | Validate + quyền + log | Quyền kiểm ở application? CSRF? Nội dung tài liệu không vào log / span / sự kiện? Đầu vào từ LLM / PDF được coi là dữ liệu? |
| **Hiệu năng** | Không đo | Có đo, chưa ngưỡng | Có ngưỡng + test tải | Ảnh hưởng NFR-01 → NFR-05? Có metric / test k6 / benchmark? Truy vấn có index? |
| **Dễ đọc** | Tên mơ hồ, hàm dài | Rõ trong file | Rõ + comment "vì sao" | Tên theo nghiệp vụ? Comment nêu lý do + mã yêu cầu, không kể lại code? |
| **Truy vết** | Không mã US/FR | Có trong commit / PR | US ↔ code ↔ test | Commit có mã? `docs/traceability.md` cập nhật? Quyết định kiến trúc mới có ADR? |

**Quy tắc merge:** tổng **≥ 10/14** và **không mục nào 0 điểm** (0 ở "Đúng AC" hoặc "An toàn" luôn là blocker, bất kể tổng).

**Thứ tự review:** AC → test → an toàn → thiết kế → dễ đọc. Đọc diff, không đọc tóm tắt. Mỗi comment trích dẫn `file:dòng` và có mức:

| Mức | Nghĩa | Merge? |
|---|---|---|
| blocker | Sai AC, lỗ hổng, mất dữ liệu, test giả | Không |
| major | Thiếu edge case / test âm, vi phạm kiến trúc, thiếu đo NFR | Sửa trước merge hoặc tạo issue có hạn, reviewer đồng ý |
| minor | Tên, comment, gọn code | Tuỳ người viết |

**Artifact bắt buộc:** PR + checklist đã tick + log CI xanh + quyết định approve (của người không viết code). Không có artifact = chưa review.

## Bảng chấm (dán vào PR)

| Tiêu chí | Điểm | Bằng chứng (`file:dòng`, test, log) |
|---|---|---|
| Đúng AC | | |
| Test | | |
| Thiết kế | | |
| An toàn | | |
| Hiệu năng | | |
| Dễ đọc | | |
| Truy vết | | |
| **Tổng** | **/14** | |
