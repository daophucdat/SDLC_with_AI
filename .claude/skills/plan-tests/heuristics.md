# 6 heuristic cắt test case từ AC

| Mã | Heuristic | Câu hỏi | Ví dụ trong repo |
|---|---|---|---|
| **H** | Happy path | Người dùng làm đúng như AC mô tả thì có đúng kết quả? | TC-201-01 tải 1 PDF → "Sẵn sàng", 3 trang |
| **V** | Biến thể dữ liệu | Dữ liệu khác loại nhưng vẫn hợp lệ: tiếng Việt có dấu, tiếng Anh, nhiều tài liệu, lô lẫn? | TC-201-02 tên file có dấu; TC-303-03 câu hỏi tiếng Anh |
| **B** | Biên | Đúng ngưỡng, ngay dưới, ngay trên (50 MB → 49,5 MB và 50 MB + 1 KB; 3 song song → 10 file) | TC-201-03, TC-201-08 |
| **N** | Đường âm | Đầu vào sai / bị chặn: sai định dạng, rỗng, giả mạo đuôi, LLM trả lời sai trích dẫn | TC-201-07…10, TC-303-06, 07 |
| **R** | Khôi phục | Lỗi giữa chừng rồi hết lỗi: mất mạng, server lỗi, câu sau lỗi — hệ thống có tự hồi phục? | TC-201-12, 13; TC-303-08 |
| **P** | Phi chức năng | Ngưỡng NFR gắn với AC: thời gian, số lần thử, giới hạn song song, a11y | TC-201-04 ≤ 300 s; TC-303-10 ≤ 30 s |

## Mẹo đã kiểm chứng (docs/bugs.md)

- **Kho dùng chung:** đừng giả định số tài liệu trong kho ("trong 2 tài liệu") — đọc N từ hệ thống (TD-1).
- **So chữ trích từ PDF theo từ**, không theo byte: PDF có no-break space (TD-2).
- **Mất mạng phải xảy ra trước khi server nhận file** — throttle của DevTools chỉ giả lập (HD-2). Ghi rõ trong bước: "file chưa tới server".
- **Đếm "đang chạy" theo đúng sự kiện mà ứng dụng dùng** để giải phóng chỗ (HD-1).
- Một TC đo phi chức năng (P) có thể chạy chung lượt với TC chức năng của nó — ghi rõ "cùng lượt với TC-…".
- TC chỉ đo được với LLM thật / staging → đánh dấu **thủ công**, không giả vờ tự động.
