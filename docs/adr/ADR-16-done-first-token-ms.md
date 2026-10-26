# ADR-16: Thêm `firstTokenMs` vào sự kiện SSE `done`

- Trạng thái: Accepted · Ngày: 2026-10-23 · Story: US-306, EN-12 · Yêu cầu: NFR-02, LG-06

## Bối cảnh
LG-06 đo p95 "phần đầu câu trả lời ≤ 5 s" bằng k6. k6 không đọc được từng sự kiện SSE; thời gian tới byte đầu (TTFB) chỉ phản ánh lúc gửi `meta`, không phải `delta` đầu tiên.

## Quyết định
Sự kiện `done` mang thêm `firstTokenMs` (số ms tới token đầu, do server đo = `answer.first_token_ms`, `null` nếu không gọi LLM). Thay đổi tương thích ngược; đã cập nhật dev_tasks.md §0.5 và các file task.

## Hệ quả
- k6, harness đánh giá và metric `qa_first_token_seconds` dùng cùng một số đo.
- Đây là số đo phía server (chưa tính mạng tới trình duyệt); Playwright đo phía client khi cần.
