# ADR-13: Hỏi đáp chia 2 pha — kiểm tra trước, rồi mới mở luồng SSE

- Trạng thái: Accepted · Ngày: 2026-10-23 · Story: US-301, US-302, EN-06

## Bối cảnh
Hợp đồng API Q2 (dev_tasks.md §0.4) yêu cầu các lỗi 400 `QUESTION_INVALID`, 409 `NO_READY_DOCUMENTS`, 429 `RATE_LIMITED`, 503 `AI_BUSY` trả về dưới dạng problem+json. Khi luồng `text/event-stream` đã bắt đầu (status 200 đã gửi) thì không thể đổi mã HTTP nữa. Giả mã gốc chiếm slot LLM *bên trong* luồng.

## Quyết định
`QuestionAnsweringService.prepare()` làm mọi kiểm tra có thể thất bại — quyền, hội thoại thuộc phiên, câu hỏi hợp lệ, giới hạn tần suất, có tài liệu READY, **chiếm slot LLM** (chờ ≤ `LLM_QUEUE_WAIT_S`) — rồi trả về `AskHandle`. Router chỉ mở `StreamingResponse` sau khi `prepare()` thành công. `AskHandle.events()` luôn trả slot trong `finally`, kể cả khi client ngắt kết nối.

## Hệ quả
- Tốt: FE nhận lỗi HTTP chuẩn trước khi có luồng; không tốn token cho câu hỏi bị từ chối.
- Xấu: slot được giữ cả khi truy xuất ra "không có đoạn" (không gọi LLM) — chấp nhận, vì truy xuất ≤ 250 ms.
- Phải làm: `events()` phải được tiêu thụ đúng một lần (router luôn làm vậy); test `test_slot_is_released_after_every_outcome`.

## Phương án đã cân nhắc
Trả lỗi bằng sự kiện `error` trong luồng — trái hợp đồng §0.5 và FE phải xử lý 2 kiểu lỗi.
