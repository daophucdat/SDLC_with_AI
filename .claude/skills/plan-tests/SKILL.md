---
name: plan-tests
description: >-
  Rút test case (TC) từ acceptance criteria (AC) của user story trong docs/ và ghi vào docs/test-cases.md, kèm
  kỳ vọng PASS / FAIL viết trước khi chạy và ma trận AC ↔ TC. Dùng khi người dùng muốn lập test case, viết test
  plan, bổ sung TC cho một story, hỏi "AC này test thế nào", "cần test những gì", hoặc phủ biên / đường âm.
when_to_use: >-
  Kích hoạt khi nói tới test case, test plan, kịch bản kiểm thử, AC-xxx.y, TC-xxx-yy, heuristic, biên, đường âm
  cho một US-xxx. Không dùng để viết code test (gen-tests) hay chạy test (run-test-case).
argument-hint: US-xxx [US-yyy …]
allowed-tools: Read Grep Glob Edit Write
---

Lập test case cho **$ARGUMENTS** (Day 6). Đầu ra là tài liệu, không phải code test.

## KHÔNG ĐƯỢC
- Không sửa AC hay bất kỳ file đặc tả baseline nào (`docs/implement/userStory.md`, `docs/02-requirements/` …). AC mơ hồ → ghi vào "AC đã rà" và hỏi.
- Không tạo TC không trỏ về đúng một AC; không viết kỳ vọng mơ hồ ("hoạt động đúng", "hiển thị ổn").
- Không đổi kỳ vọng của TC đã chạy để khớp kết quả — chỉ thêm một dòng "Lịch sử sửa" có phiếu trong `docs/bugs.md`.
- Không viết code test, không chạy test trong skill này.

## Ngữ cảnh
- Story có trong repo: !`grep -n "^### US-" docs/implement/userStory.md | head -60`
- TC đã có: !`grep -o "TC-[0-9]\{3\}-[0-9]\{2\}" docs/test-cases.md 2>/dev/null | sort -u | tr '\n' ' ' || echo "chưa có"`

## Quy trình
1. Đọc AC của story trong `docs/implement/userStory.md`, ràng buộc liên quan (NFR, EC, BR) trong `docs/implement/dev_tasks.md` Phần 0 và hành vi hiện có (`docs/traceability.md`).
2. Mỗi AC → 2–6 TC theo 6 heuristic trong [heuristics.md](heuristics.md). Bắt buộc có ít nhất một **N** (âm) hoặc **B** (biên) cho mỗi AC có giới hạn số.
3. Mỗi TC theo [template.md](template.md): mã `TC-<story>-<nn>`, AC gốc, heuristic, tiền điều kiện, bước có **dữ liệu cụ thể** (tên file, kích thước, câu hỏi), cột **PASS khi** / **FAIL khi** đo được.
4. Ghi vào `docs/test-cases.md` (giữ TC cũ, đánh số tiếp), cập nhật **ma trận AC ↔ TC** cuối file và "AC đã rà".
5. Dữ liệu test mới → thêm vào `e2e/fixtures/build_fixtures.py` (tên file khác nhau giữa các TC — kho dùng chung).
6. Báo cáo ngắn: số TC mới theo AC × heuristic, AC còn thiếu phủ, câu hỏi mở.
