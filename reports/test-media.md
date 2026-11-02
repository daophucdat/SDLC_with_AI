# Video / GIF các test case — lượt `run2`

Sinh bởi `python scripts/test_media.py` từ `reports/results-run2.json` — không sửa tay.
GIF dựng từ screencast trong trace (≤ 8 khung/s, khoảng lặng > 2 s rút còn 2 s); video `.webm` là bản đủ thời lượng. Bảng kết quả: [test-report.md](test-report.md).

## TC-201-01 [AC-201.1][H] chọn 1 PDF bằng nút Tải tài liệu → xuất hiện, Sẵn sàng, 3 trang — PASS

![TC-201-01](gifs/run2/TC-201-01.gif)

[video .webm](videos/run2/TC-201-01.webm)

## TC-201-02 [AC-201.1][V] kéo-thả file tên tiếng Việt có dấu → tên giữ nguyên, Sẵn sàng — PASS

![TC-201-02](gifs/run2/TC-201-02.gif)

[video .webm](videos/run2/TC-201-02.webm)

## TC-201-03 TC-201-04 [AC-201.1][B][P] PDF 49,5 MB: thấy % tiến độ tăng dần; Sẵn sàng ≤ 300 s — PASS

![TC-201-03+TC-201-04](gifs/run2/TC-201-03+TC-201-04.gif)

[video .webm](videos/run2/TC-201-03+TC-201-04.webm)

## TC-201-05 [AC-201.2][H] chọn 10 PDF cùng lúc → 10 dòng, tối đa 3 tải song song, cả 10 Sẵn sàng — PASS

![TC-201-05](gifs/run2/TC-201-05.gif)

[video .webm](videos/run2/TC-201-05.webm)

## TC-201-06 [AC-201.2][V] 9 PDF hợp lệ + 1 PDF hỏng → 9 Sẵn sàng, 1 Lỗi có lý do, không ảnh hưởng nhau — PASS

![TC-201-06](gifs/run2/TC-201-06.gif)

[video .webm](videos/run2/TC-201-06.webm)

## TC-201-07 [AC-201.3][N] ảnh .png → từ chối ở trình duyệt, không có request tải lên — PASS

![TC-201-07](gifs/run2/TC-201-07.gif)

[video .webm](videos/run2/TC-201-07.webm)

## TC-201-08 [AC-201.3][B] PDF 50 MB + 1 KB → báo vượt 50 MB, không tải lên — PASS

![TC-201-08](gifs/run2/TC-201-08.gif)

[video .webm](videos/run2/TC-201-08.webm)

## TC-201-09 [AC-201.3][N] file .doc đổi đuôi .pdf → máy chủ từ chối, không vào kho — PASS

![TC-201-09](gifs/run2/TC-201-09.gif)

[video .webm](videos/run2/TC-201-09.webm)

## TC-201-10 [AC-201.3][N] PDF 0 byte → bị từ chối kèm lý do — PASS

![TC-201-10](gifs/run2/TC-201-10.gif)

[video .webm](videos/run2/TC-201-10.webm)

## TC-201-11 [AC-201.3][V] lô lẫn hợp lệ / không hợp lệ → chỉ file hợp lệ được tải — PASS

![TC-201-11](gifs/run2/TC-201-11.gif)

[video .webm](videos/run2/TC-201-11.webm)

## TC-201-12 [AC-201.4][R] mất mạng giữa lúc tải → tạm dừng → có mạng lại tự tải tiếp — PASS

![TC-201-12](gifs/run2/TC-201-12.gif)

[video .webm](videos/run2/TC-201-12.webm)

## TC-201-13 [AC-201.4][R] mất mạng quá 3 lần thử → Tải lên thất bại + Thử lại → Sẵn sàng — PASS

![TC-201-13](gifs/run2/TC-201-13.gif)

[video .webm](videos/run2/TC-201-13.webm)

## TC-303-01 TC-303-10 [AC-303.1][H][P] mỗi đoạn có trích dẫn; mục Nguồn 'Tên — trang X'; ≤ 30 s, phần đầu ≤ 5 s — PASS

![TC-303-01+TC-303-10](gifs/run2/TC-303-01+TC-303-10.gif)

[video .webm](videos/run2/TC-303-01+TC-303-10.webm)

## TC-303-02 [AC-303.1][V] câu cần 2 tài liệu → mỗi đoạn có trích dẫn, Nguồn có cả 2 tài liệu — PASS

![TC-303-02](gifs/run2/TC-303-02.gif)

[video .webm](videos/run2/TC-303-02.webm)

## TC-303-03 [AC-303.1][V] câu hỏi tiếng Anh → trả lời tiếng Anh, vẫn đủ trích dẫn — PASS

![TC-303-03](gifs/run2/TC-303-03.gif)

[video .webm](videos/run2/TC-303-03.webm)

## TC-303-04 [AC-303.2][H] mỗi chip mở đúng tài liệu, đúng trang, đoạn trích được tô sáng — PASS

![TC-303-04](gifs/run2/TC-303-04.gif)

[video .webm](videos/run2/TC-303-04.webm)

## TC-303-06 [AC-303.3][N] LLM trả lời không có trích dẫn → 'không tìm thấy', không còn chữ của LLM — PASS

![TC-303-06](gifs/run2/TC-303-06.gif)

[video .webm](videos/run2/TC-303-06.webm)

## TC-303-07 TC-303-08 [AC-303.3][N][R] trích dẫn số không tồn tại → 'không tìm thấy'; câu sau vẫn bình thường — PASS

![TC-303-07+TC-303-08](gifs/run2/TC-303-07+TC-303-08.gif)

[video .webm](videos/run2/TC-303-07+TC-303-08.webm)

## TC-303-09 [AC-303.4][H] dữ liệu lưu: trang và đoạn trích lấy từ PDF, không lấy từ chữ LLM viết — PASS

![TC-303-09](gifs/run2/TC-303-09.gif)

[video .webm](videos/run2/TC-303-09.webm)
