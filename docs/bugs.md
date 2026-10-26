# Phiếu lỗi — đợt test US-201, US-303 (2026-10-26)

Mỗi FAIL trong [reports/test-report.md](../reports/test-report.md) có một phiếu ở đây, kể cả khi lỗi nằm ở test chứ không ở sản phẩm. Lỗi lọt qua các cổng (escaped defect) ghi thêm ở [docs/quality/escaped_defects.md](quality/escaped_defects.md).

Loại: **BUG** lỗi sản phẩm · **TD** lỗi test case (kỳ vọng / dữ liệu sai) · **HD** lỗi bộ chạy test / môi trường · **OBS** quan sát ngoài AC, chờ PO.

Quy tắc khi một TC FAIL: (1) giữ nguyên kỳ vọng, (2) chứng minh nguyên nhân bằng dữ liệu — log, ảnh chụp, timeline request, (3) chỉ khi chứng minh được phép đo hoặc kỳ vọng sai mới sửa test, và ghi lại ở đây + lịch sử sửa của [docs/test-cases.md](test-cases.md); nếu sản phẩm sai → BUG, sửa code, thêm test ở tầng thấp nhất bắt được nó.

| Mã | Loại | TC | Mức | Trạng thái |
|---|---|---|---|---|
| HD-1 | HD | TC-201-05 | Cao (báo sai một lỗi sản phẩm không có) | Đã sửa |
| HD-2 | HD | TC-201-12, TC-201-13 | Cao (test kịch bản khác với AC) | Đã sửa |
| HD-3 | HD | tất cả | Trung bình | Đã sửa |
| HD-4 | HD | TC-303-01, 06, 07, 08, 10 | Trung bình | Đã sửa |
| TD-1 | TD | TC-303-06 | Thấp | Đã sửa TC |
| TD-2 | TD | TC-303-09 | Thấp | Đã sửa TC |
| OBS-1 | OBS | (ngoài AC-201.4) | Thấp | **Mở — chờ PO** |

Lỗi sản phẩm (BUG): **không có** trong phạm vi 8 AC đã test.

---

## HD-1 · Đếm upload song song thừa một

- **Thấy:** TC-201-05 FAIL "maxInFlight 4 > 3", lặp lại 2 lần — kể cả khi chuyển từ sự kiện `request`/`requestfinished` của Playwright sang đếm trong trang theo XHR `loadend`.
- **Nguyên nhân (chứng minh bằng code):** `web/src/api-client/documents.ts` resolve promise trong `xhr.onload`; `uploadQueue.ts` `.finally(() => pump())` chạy ở microtask ngay sau `onload`, nên `send()` của file kế tiếp xảy ra **trước** sự kiện `loadend` của file vừa xong. Lúc đó file cũ đã nhận đủ phản hồi — chỉ có 3 upload thực sự đang chạy.
- **Sửa:** `e2e/specs/tc-helpers.ts` `uploadMonitor` tính một upload là xong ở `readyState === 4` (bắn trước `load`). Kết quả: tối đa 3, cả 2 lượt.
- **Sản phẩm:** đúng giới hạn 3 (T201.5); `uploadQueue.test.ts` đã kiểm tra ở tầng unit.
- **Bài học:** một bộ đếm "đang chạy" phải kết thúc ở đúng sự kiện mà ứng dụng dùng để giải phóng chỗ.

## HD-2 · Throttle upload của DevTools không chặn được byte tới server

- **Thấy:** TC-201-13 FAIL — kho có **hai** dòng `Lon_8MB_b.pdf`: một "Tải lên thất bại", một "Sẵn sàng".
- **Nguyên nhân (timeline):** request upload lúc 36 ms; chuyển offline lúc 66 ms; trình duyệt báo `ERR_INTERNET_DISCONNECTED` lúc 272 ms — nhưng server đã liệt kê file `READY` lúc 444 ms. `Network.emulateNetworkConditions` của Chromium chỉ **giả lập** tốc độ upload (byte đi hết tốc độ, phản hồi bị giữ lại), nên "mất mạng giữa lúc tải" thực ra là "mất phản hồi sau khi server đã lưu" — một kịch bản khác AC-201.4.
- **Sửa:** `dropUploads(page)` giữ upload "đang bay" bằng `page.route` rồi `abort("internetdisconnected")` khi cắt mạng — file không tới server. TC-201-12/13 thêm kiểm tra "chỉ 1 dòng" và TC-201-13 kiểm tra **đúng 4** lần gửi.
- **Hệ quả cho số đo:** TC-201-04 (49,5 MB tới "Sẵn sàng") đo trên localhost với throttle giả lập → con số lạc quan; ghi rõ trong báo cáo.
- **Phát sinh:** OBS-1.

## HD-3 · Bộ test dùng nhầm dev server của dự án khác

- **Thấy:** lần chạy 5 — hai test đầu FAIL, không có nút `#login-member`; ảnh chụp là trang 404 của một ứng dụng khác đang chạy trên :5173.
- **Nguyên nhân:** `webServer.reuseExistingServer: true` chấp nhận bất kỳ thứ gì đang nghe ở cổng đó.
- **Sửa:** stack cục bộ dùng cổng riêng (`E2E_WEB_PORT`, mặc định 5180; `E2E_API_PORT` 8000), không bao giờ reuse; `e2e_server.py` nhận `E2E_WEB_BASE`.

## HD-4 · Playwright không đọc được body SSE

- **Thấy:** lần chạy 1 — TC-303-06 FAIL `Protocol error (Network.getResponseBody): No data found for resource`.
- **Nguyên nhân:** `response.text()` lấy body từ DevTools; với response streaming (SSE) Chromium không giữ lại body.
- **Sửa:** `captureAnswers(page)` bọc `window.fetch` trong trang, `tee()` stream của `/questions` và lưu bản sao; test đọc sự kiện `done` từ đó.

## TD-1 · TC-303-06 giả định kho chỉ có 2 tài liệu

- **Thấy:** kỳ vọng "Không tìm thấy thông tin này trong **2** tài liệu hiện có"; app ghi "…trong **14**…" (lần 2), "…**25**…" (lần 3).
- **Nguyên nhân:** tiền điều kiện của TC sai: US-303 chạy trên cùng kho với US-201 (kho dùng chung cả đội là đặc tính của sản phẩm). N là **số tài liệu Sẵn sàng** (`WorkspacePage.readyCount`) — 25, không phải tổng kho 26 (có `Hong.pdf` lỗi). Hành vi sản phẩm đúng EC-14.
- **Sửa:** kỳ vọng thành "trong N tài liệu hiện có, N = số tài liệu Sẵn sàng" (đọc qua API). Ghi ở lịch sử sửa của test-cases.md.

## TD-2 · TC-303-09 so khớp từng byte với chữ PDF

- **Thấy:** `excerpt` hiển thị "Điều 5. Thanh toán: …" nhưng `toContain("Thanh toán")` FAIL.
- **Nguyên nhân:** khoảng trắng trong excerpt là U+00A0 — đúng như chữ trong PDF (kiểm bằng PyMuPDF trực tiếp). Excerpt là chữ PDF nguyên văn, đúng AC-303.4; retrieval đã chuẩn hoá khoảng trắng (`" ".join(text.split())`), highlight (TC-303-04) PASS.
- **Sửa:** so khớp sau khi gộp khoảng trắng, với câu dài hơn ("Thanh toán: khách hàng thanh toán 30%") để kiểm tra chặt hơn.

## OBS-1 · Mất kết nối sau khi server đã lưu file

- **Thấy (HD-2, lần 3):** hàng đợi báo "Tải lên thất bại — Kiểm tra kết nối rồi thử lại" trong khi kho đã có cùng file "Sẵn sàng". Bấm "Thử lại" sẽ gửi lại một file trùng (sẽ đi vào luồng trùng lặp US-204 khi bật cờ `duplicate`).
- **Vì sao không phải BUG:** AC-201.4 chỉ nói về mất mạng *trong lúc tải*; trình duyệt không thể biết server đã lưu hay chưa khi phản hồi bị mất.
- **Đề xuất cho PO:** sau khi có mạng lại, hàng đợi gọi `GET /documents?q=<tên>` và gỡ dòng lỗi nếu file đã có với cùng kích thước — hoặc chấp nhận hành vi hiện tại vì US-204 đã chặn bản trùng. Khi PO quyết định → thêm AC + TC-201-14.
