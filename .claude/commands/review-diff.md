---
description: Review L1 (tư vấn) theo rubric — chấm diff, trích dẫn dòng, không approve
argument-hint: "[git range, mặc định origin/main...HEAD]"
---

Thực hiện **L1 agent review** cho diff `${ARGUMENTS:-origin/main...HEAD}` theo `docs/quality/code_review_rubric.md`. Đây là review tư vấn: được đề xuất sửa, **không được approve hay merge**.

1. `git diff --stat $RANGE` và `git log --format='%h %s' $RANGE`. Đọc **diff**, không đọc tóm tắt; mở file đầy đủ khi cần ngữ cảnh.
2. Xác định story / AC mà diff phục vụ (từ commit, PR, `docs/traceability.md`). Hỏi với từng test mới: *test này chứng minh AC nào?*
3. Review theo thứ tự: **Đúng AC → Test → An toàn → Thiết kế → Hiệu năng → Dễ đọc → Truy vết**. Kiểm tra riêng:
   - test bị nới hoặc sửa cho pass (assertion yếu đi, `skip`, ngưỡng hạ);
   - nội dung tài liệu / câu hỏi lọt vào log, metric, span (TC-08);
   - kiểm tra quyền ở tầng application, không chỉ ở router;
   - thay đổi hợp đồng API so với `docs/implement/dev_tasks.md` §0 mà không có ADR.
4. Chạy `make check` (hoặc các lệnh tương ứng) và đính kèm kết quả.
5. Kết quả trả về:
   - **Điểm rubric**: bảng 7 tiêu chí × điểm 0–2 × bằng chứng (`file:dòng`). Tổng /14.
   - **Comment**: mỗi comment có mức `blocker` / `major` / `minor`, trích dẫn `file:dòng`, nêu vấn đề và đề xuất sửa cụ thể.
   - **Kết luận**: "Đủ điều kiện chuyển sang L2" chỉ khi tổng ≥ 10/14 **và** không mục nào 0 điểm; ngược lại liệt kê blocker.
