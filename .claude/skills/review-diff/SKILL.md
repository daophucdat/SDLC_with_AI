---
name: review-diff
description: >-
  Review L1 (tư vấn) một diff / nhánh / PR theo rubric docs/quality/code_review_rubric.md: chấm 7 tiêu chí 0–2,
  comment blocker / major / minor kèm file:dòng, không approve. Dùng khi người dùng muốn review code, xem lại
  thay đổi, chấm diff, kiểm tra PR trước khi gửi người duyệt.
argument-hint: "[git range, mặc định origin/main...HEAD]"
allowed-tools: Read Grep Glob Bash(git diff*) Bash(git log*) Bash(git show*) Bash(bash scripts/dev.sh check*)
disallowed-tools: Edit Write NotebookEdit
---

**L1 agent review** cho `${ARGUMENTS:-origin/main...HEAD}` theo `docs/quality/code_review_rubric.md`.

## KHÔNG ĐƯỢC
- Không approve, không merge, không sửa code — review chỉ là tư vấn.
- Không review theo tóm tắt hay commit message: đọc **diff**, mở file đầy đủ khi cần.
- Không cho điểm không có bằng chứng `file:dòng`.

## Quy trình
1. `git diff --stat <range>` và `git log --format='%h %s' <range>`.
2. Xác định story / AC diff phục vụ. Với từng test mới: *test này chứng minh AC nào?*
3. Thứ tự: **Đúng AC → Test → An toàn → Thiết kế → Hiệu năng → Dễ đọc → Truy vết**. Kiểm riêng:
   - test bị nới hoặc sửa cho pass (assertion yếu đi, `skip`, ngưỡng hạ, kỳ vọng TC đổi không có phiếu);
   - nội dung tài liệu / câu hỏi lọt vào log, metric, span (TC-08);
   - kiểm tra quyền ở tầng application, không chỉ router;
   - đổi hợp đồng API so với `docs/implement/dev_tasks.md` §0 mà không có ADR.
4. Chạy `bash scripts/dev.sh check` và đính kèm kết quả.
5. Trả về: **Điểm rubric** (7 tiêu chí × 0–2 × bằng chứng, tổng /14) · **Comment** (mức, `file:dòng`, vấn đề, đề xuất) · **Kết luận**: "Đủ điều kiện chuyển sang L2" chỉ khi ≥ 10/14 **và** không mục nào 0.
