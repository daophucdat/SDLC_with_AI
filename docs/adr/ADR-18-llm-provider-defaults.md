# ADR-18: Cấu hình mặc định của LLM và adapter giả lập

- Trạng thái: Accepted · Ngày: 2026-10-23 · Story: EN-06 · Liên quan: ADR-09, OQ-008

## Quyết định
- `LLM_PROVIDER=fake` là mặc định cho dev / CI: trả lời từ chính các đoạn được truy xuất, có kịch bản `#notfound`, `#badref`, `#503`, `#slow`, `#hang` để test mọi nhánh mà không tốn tiền và không cần mạng. `fake` bị từ chối khi `ENVIRONMENT=prod`.
- Claude API: `LLM_MODEL=claude-sonnet-5-5` (theo dev_tasks §0.2), `effort=low` (câu trả lời ngắn, ưu tiên NFR-02), **không gửi `temperature`** (model hiện tại từ chối giá trị khác mặc định), bật refusal fallback phía server. SDK `max_retries=0`: chính sách thử lại nằm ở `ResilientGenerator` (1 lần, chỉ trước token đầu).
- Phương án nội bộ: `openai_compatible` (vLLM / TGI) cùng port.

## Hệ quả
- Đổi model / effort chỉ qua biến môi trường; mỗi lần đổi phải chạy lại EN-10 và so sánh KR2.1 → KR2.3.
- LG-12 (cam kết không huấn luyện) là điều khoản hợp đồng của tổ chức, không phải tham số request.
