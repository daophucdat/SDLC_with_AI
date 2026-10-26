# Test case — US-201, US-303

Test plan: [docs/test-plan.md](test-plan.md). Mỗi TC trỏ về đúng một AC; **kỳ vọng PASS / FAIL được ghi ở đây trước khi chạy** và không đổi sau khi thấy kết quả. Spec Playwright mang mã TC trong tên test (`TC-201-01 …`), nên báo cáo nối thẳng về dòng dưới đây.

Heuristic (Day 6): **H** happy path · **V** biến thể dữ liệu · **B** giới hạn biên · **N** đường âm · **R** khôi phục · **P** phi chức năng.

Tiền điều kiện chung: app test (test-plan §5) vừa khởi động, kho trống; đăng nhập `member`.

## US-201 · Tải một hoặc nhiều file PDF

| TC | AC | H | Bước | PASS khi (ghi trước) | FAIL khi |
|---|---|---|---|---|---|
| TC-201-01 | AC-201.1 | H | Bấm "Tải tài liệu", chọn `HopDong_ABC.pdf` (3 trang) | Dòng `HopDong_ABC.pdf` xuất hiện trong kho ≤ 2 s; sau đó badge "Sẵn sàng", meta "3 trang", "Bạn" ≤ 30 s | Không có dòng, hoặc dừng ở trạng thái khác, hoặc sai số trang |
| TC-201-02 | AC-201.1 | V | Kéo-thả file `Hợp đồng ABC – bản ký.pdf` (tên tiếng Việt có dấu, gạch dài) vào danh sách | Tên hiển thị đúng từng ký tự; đạt "Sẵn sàng" | Tên bị biến đổi / mất dấu, hoặc không nhận khi kéo-thả |
| TC-201-03 | AC-201.1 | B | Mạng tải lên giả lập ~4 MB/s; chọn PDF hợp lệ **49,5 MB** | Trong lúc tải: badge "Đang tải lên N%" với 0 < N < 100, `progressbar` có `aria-valuenow` tăng dần; cuối cùng không bị từ chối | Không thấy %, % không tăng, hoặc bị báo vượt 50 MB |
| TC-201-04 | AC-201.1 | P | (cùng lượt với TC-201-03) đo từ lúc chọn file tới "Sẵn sàng" | ≤ 300 s (NFR-03, môi trường cục bộ) | > 300 s hoặc lỗi |
| TC-201-05 | AC-201.2 | H | Chọn cùng lúc 10 PDF hợp lệ khác nội dung | 10 dòng, mỗi dòng có badge riêng; **không quá 3** yêu cầu `POST /documents` chạy đồng thời; cả 10 đạt "Sẵn sàng" | Thiếu dòng, > 3 upload song song, hoặc có file không đạt |
| TC-201-06 | AC-201.2 | V | Chọn cùng lúc 9 PDF hợp lệ khác (`TaiLieu_11`–`19`) + 1 PDF hỏng (đầu `%PDF-` nhưng nội dung hỏng) | 9 dòng "Sẵn sàng", dòng file hỏng "Lỗi" kèm "File bị hỏng hoặc không mở được." — các file không ảnh hưởng nhau | File hỏng làm hỏng file khác, hoặc không có lý do |
| TC-201-07 | AC-201.3 | N | Chọn `anh.png` | Toast "anh.png: Chỉ hỗ trợ file PDF."; **không có** `POST /documents`; không có dòng trong kho | Có request tải lên, hoặc file vào kho |
| TC-201-08 | AC-201.3 | B | Chọn PDF **50 MB + 1 KB** | Toast "… File vượt 50 MB. Hãy tách file hoặc liên hệ trưởng nhóm."; không có `POST /documents` | Tải lên bắt đầu, hoặc không có lý do |
| TC-201-09 | AC-201.3 | N | Chọn `Word_doi_duoi.pdf` (nội dung .doc, đuôi .pdf) | Máy chủ từ chối: toast "… Chỉ hỗ trợ file PDF."; kho không có dòng | File vào kho |
| TC-201-10 | AC-201.3 | N | Chọn `Rong.pdf` (0 byte) | Bị từ chối kèm lý do; kho không có dòng | File vào kho hoặc lỗi không có thông báo |
| TC-201-11 | AC-201.3 | V | Chọn cùng lúc `BaoGia_XYZ.pdf`, `anh.png`, file 50 MB + 1 KB | 2 toast từ chối đúng lý do; `BaoGia_XYZ.pdf` vẫn đạt "Sẵn sàng" | File hợp lệ bị chặn theo, hoặc thiếu lý do |
| TC-201-12 | AC-201.4 | R | Chọn PDF 8 MB; khi đang tải (file **chưa tới server**) → **mất mạng** 2 s → có mạng lại ‹sửa r1, HD-2› | Thấy "Tạm dừng — mất kết nối"; sau khi có mạng, tự tải tiếp và đạt "Sẵn sàng" mà người dùng không phải làm gì; kho có đúng 1 dòng file đó | Kẹt ở tạm dừng, mất file, hoặc phải tải lại tay |
| TC-201-13 | AC-201.4 | R | Chọn PDF 8 MB khác (file **chưa tới server**); mất mạng **> 14 s** (quá 3 lần thử 2/4/8 s) → có mạng lại → menu "Thử lại" | Đúng 1 lần gửi + 3 lần thử; rồi "Tải lên thất bại" + thông điệp kiểm tra kết nối + mục "Thử lại"; bấm "Thử lại" → "Sẵn sàng", 1 dòng | Thử quá 3 lần, không có nút thử lại, hoặc thử lại không chạy |

## US-303 · Mỗi ý có trích dẫn tài liệu và trang

Tiền điều kiện thêm: `HopDong_ABC.pdf` và `BaoGia_XYZ.pdf` đã "Sẵn sàng".

| TC | AC | H | Bước | PASS khi (ghi trước) | FAIL khi |
|---|---|---|---|---|---|
| TC-303-01 | AC-303.1 | H | Hỏi "Điều khoản thanh toán của hợp đồng ABC là gì?" | Mỗi đoạn của câu trả lời có ≥ 1 chip trích dẫn `[n]`; cuối thẻ có mục "Nguồn" với dòng "HopDong_ABC.pdf — trang 2" | Có đoạn không trích dẫn, không có mục Nguồn, hoặc định dạng khác "Tên — trang X" |
| TC-303-02 | AC-303.1 | V | Hỏi câu cần 2 tài liệu: "Thanh toán hợp đồng ABC và đơn giá triển khai báo giá XYZ?" | Mỗi đoạn có chip; mục Nguồn có **cả** `HopDong_ABC.pdf` và `BaoGia_XYZ.pdf` | Chỉ một tài liệu, hoặc đoạn thiếu chip |
| TC-303-03 | AC-303.1 | V | Hỏi tiếng Anh "What are the payment terms of the ABC contract?" | Câu trả lời tiếng Anh ("According to the documents…"), vẫn đủ chip và mục Nguồn | Mất trích dẫn khi đổi ngôn ngữ |
| TC-303-04 | AC-303.2 | H | Với mỗi chip của TC-303-01 và TC-303-02: bấm chip | Vùng nguồn mở **đúng tài liệu, đúng trang** ghi ở chip; đoạn trích được tô sáng và chứa từ khoá của ý (vd. "30%") | Mở sai tài liệu / sai trang, hoặc không tô sáng được |
| TC-303-05 | AC-303.2 | P | **Thủ công trên staging, LLM thật:** chọn ngẫu nhiên 30 trích dẫn từ `eval/run_eval.py`, mở từng trang | ≥ 27/30 trang chứa đúng thông tin (≥ 90%, LG-05) | < 27/30 |
| TC-303-06 | AC-303.3 | N | Hỏi câu khiến LLM trả lời **không có trích dẫn** (kịch bản `#noref` của LLM giả lập) | Thẻ trung tính "Không tìm thấy thông tin này trong N tài liệu hiện có", **N = số tài liệu Sẵn sàng trong kho** ‹sửa r1, TD-1›; không còn chữ do LLM viết; không có mục Nguồn | Hiện câu trả lời không trích dẫn |
| TC-303-07 | AC-303.3 | N | Hỏi câu khiến LLM trích dẫn **số không có trong ngữ cảnh** (`#badref`) | Như TC-303-06 | Hiện số trích dẫn không tồn tại |
| TC-303-08 | AC-303.3 | R | Ngay sau TC-303-07, cùng hội thoại, hỏi lại câu của TC-303-01 | Câu trả lời bình thường, đủ chip và Nguồn — lỗi trước không làm hỏng hội thoại | Thẻ lỗi / không tìm thấy lan sang câu sau |
| TC-303-09 | AC-303.4 | H | Sau TC-303-01, đọc dữ liệu đã lưu: `GET /api/v1/conversations/{id}/questions` | Mỗi trích dẫn có `fileName`, `page` = trang thật trong PDF, `excerpt` là **đoạn văn trong PDF** (so theo từ, khoảng trắng gộp — PDF dùng no-break space ‹sửa r1, TD-2›; không chứa câu dẫn "Theo tài liệu:" do LLM viết) | Excerpt lấy từ chữ LLM, hoặc trang không khớp PDF |
| TC-303-10 | AC-303.1 | P | Đo trong TC-303-01 qua sự kiện SSE `done` | `latencyMs` ≤ 30 000 (NFR-01) và `firstTokenMs` ≤ 5 000 (NFR-02) | Vượt ngưỡng |

## Ma trận AC ↔ TC

| AC | TC | Số TC | Heuristic phủ |
|---|---|---|---|
| AC-201.1 | TC-201-01, 02, 03, 04 | 4 | H, V, B, P |
| AC-201.2 | TC-201-05, 06 | 2 | H, V |
| AC-201.3 | TC-201-07, 08, 09, 10, 11 | 5 | N, B, V |
| AC-201.4 | TC-201-12, 13 | 2 | R |
| AC-303.1 | TC-303-01, 02, 03, 10 | 4 | H, V, P |
| AC-303.2 | TC-303-04, 05 | 2 | H, P (thủ công) |
| AC-303.3 | TC-303-06, 07, 08 | 3 | N, R |
| AC-303.4 | TC-303-09 | 1 | H (dữ liệu) |

8/8 AC có TC; 23/23 TC trỏ về một AC. AC-201.2 và AC-201.4 chỉ có 2 TC vì phần biên (11 file, 4 lần thử) đã thuộc TC-201-05 (giới hạn 3 song song) và TC-201-13 (quá 3 lần thử). AC-303.4 là AC về dữ liệu lưu: các TC khác của US-303 cũng gián tiếp kiểm tra nó qua TC-303-04.

**AC đã rà khi cắt TC:** AC-303.1 "mỗi đoạn" được hiểu theo ALG-3 (đoạn = khối cách nhau bởi dòng trống) — thống nhất với `docs/implement/dev_tasks.md`; không cần sửa AC. AC-303.2 chỉ đo được trên LLM thật → TC-303-05 thủ công trên staging.

## Lịch sử sửa (sau khi chạy)

Kỳ vọng chỉ được sửa khi **chứng minh được** kỳ vọng hoặc cách đo sai — không phải vì muốn test xanh. Mỗi lần sửa có phiếu trong [docs/bugs.md](bugs.md).

| Bản | Ngày | TC | Sửa gì | Vì sao | Phiếu |
|---|---|---|---|---|---|
| r0 | 2026-10-26 | tất cả | Bản viết trước khi chạy | — | — |
| r1 | 2026-10-26 | TC-303-06 | "2 tài liệu" → "N tài liệu, N = số tài liệu Sẵn sàng" | Tiền điều kiện sai: kho dùng chung với US-201; sản phẩm đúng EC-14 | TD-1 |
| r1 | 2026-10-26 | TC-303-09 | So excerpt theo từ | Excerpt là chữ PDF nguyên văn có U+00A0 — đúng AC-303.4 | TD-2 |
| r1 | 2026-10-26 | TC-201-12, 13 | Cắt mạng trước khi file tới server; thêm "1 dòng", "đúng 4 lần gửi" | Throttle DevTools để byte tới server → test sai kịch bản; kiểm tra chặt hơn, không lỏng hơn | HD-2 |
