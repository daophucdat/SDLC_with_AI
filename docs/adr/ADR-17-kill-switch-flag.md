# ADR-17: Cờ `qa_off` tắt hỏi đáp không cần deploy

- Trạng thái: Accepted · Ngày: 2026-10-23 · Story: REL-03

## Bối cảnh
Kế hoạch ra mắt (implement_plan §9) yêu cầu "có thể tắt nhanh". Rút quyền trên IdP chỉ chặn lần đăng nhập mới; phiên đang mở sống tới 8 giờ (DQ-03).

## Quyết định
`FEATURE_FLAGS=…,qa_off` → `prepare()` trả 503 `AI_BUSY` trước mọi lời gọi LLM; `/me` báo cờ để FE vô hiệu ô câu hỏi và hiện banner "Hỏi đáp tạm gián đoạn". Kho tài liệu và trang nguồn vẫn dùng được.

## Hệ quả
- Tắt trong < 5 phút (đổi biến môi trường + khởi động lại `api`); test `test_kill_switch_turns_qa_off_but_keeps_the_library` và test FE tương ứng.
- Cờ đọc lúc khởi động; muốn đổi tức thì cần cơ chế cờ động — chưa cần cho MVP.
