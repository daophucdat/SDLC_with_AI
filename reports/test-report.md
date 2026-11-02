# Báo cáo chạy test case — US-201, US-303

Kế hoạch: [docs/test-plan.md](../docs/test-plan.md) · Test case (kỳ vọng ghi trước khi chạy): [docs/test-cases.md](../docs/test-cases.md) · Lỗi: [docs/bugs.md](../docs/bugs.md) · Truy vết: [docs/traceability.md](../docs/traceability.md)

| | |
|---|---|
| Ngày chạy | 2026-11-02 (chạy lại có ghi video; lượt đầu 2026-10-26) |
| Mã nguồn | `main` @ 49d3fe2 + bật video, `outputDir` theo lượt |
| Môi trường | App test cục bộ (`backend/tests/e2e_server.py`: FastAPI + repo trong bộ nhớ + PyMuPDF thật + LLM giả lập; Vite dev server :5180) |
| Công cụ | Playwright 1.40.1 · Chromium · Node 16.17.1 · Python 3.10.6 · Windows 11 |
| Lệnh | `cd e2e && E2E_RUN=run1 npm run test:tc` rồi `E2E_RUN=run2 npm run test:tc`; video + GIF: `python scripts/test_media.py`; bảng dưới: `python scripts/test_report.py` |
| Retry | 0 (playwright.config.ts) — mỗi PASS là PASS ngay lần đầu |
| Thô | `reports/junit-run1.xml`, `reports/junit-run2.xml` (19 test, 0 failure, ~130 s mỗi lượt khi có video) · `reports/results-run*.json` · trace: `e2e/test-results/<run>/` (không commit) |
| Video / GIF | Mỗi test một video `.webm` (1280×800, đủ thời lượng) và một GIF (720 px, ≤ 8 khung/s) — cột "Bằng chứng" dưới đây; xem tất cả GIF trong [test-media.md](test-media.md) |

## Kết quả

22 TC tự động nằm trong 19 test Playwright (TC-201-03+04, TC-303-01+10, TC-303-07+08 chạy chung một lượt vì TC sau đo trên đúng lượt của TC trước). TC-303-05 là TC thủ công trên staging với LLM thật — **chưa chạy** (không có staging trong môi trường học), xem "Chưa phủ".

<!-- results:start -->
| TC | run1 | run2 | Thời gian (s) | Đo được | Bằng chứng (run2) |
|---|---|---|---|---|---|
| TC-201-01 | PASS | PASS | 8.4 / 8.4 |  | [TC-201-01](screenshots/run2/TC-201-01.png) [GIF](gifs/run2/TC-201-01.gif) [video](videos/run2/TC-201-01.webm) |
| TC-201-02 | PASS | PASS | 7.3 / 7.1 |  | [TC-201-02](screenshots/run2/TC-201-02.png) [GIF](gifs/run2/TC-201-02.gif) [video](videos/run2/TC-201-02.webm) |
| TC-201-03 | PASS | PASS | 9.4 / 8.3 | TC-201-04 measured: 5.1 s to READY | [TC-201-03](screenshots/run2/TC-201-03.png) [GIF](gifs/run2/TC-201-03+TC-201-04.gif) [video](videos/run2/TC-201-03+TC-201-04.webm) |
| TC-201-04 | PASS | PASS | 9.4 / 8.3 | TC-201-04 measured: 5.1 s to READY | [TC-201-04](screenshots/run2/TC-201-04.png) [GIF](gifs/run2/TC-201-03+TC-201-04.gif) [video](videos/run2/TC-201-03+TC-201-04.webm) |
| TC-201-05 | PASS | PASS | 7.5 / 7.4 | max uploads in flight: 3 | [TC-201-05-queue](screenshots/run2/TC-201-05-queue.png) [TC-201-05](screenshots/run2/TC-201-05.png) [GIF](gifs/run2/TC-201-05.gif) [video](videos/run2/TC-201-05.webm) |
| TC-201-06 | PASS | PASS | 7.2 / 8.1 |  | [TC-201-06](screenshots/run2/TC-201-06.png) [GIF](gifs/run2/TC-201-06.gif) [video](videos/run2/TC-201-06.webm) |
| TC-201-07 | PASS | PASS | 2.7 / 2.9 |  | [TC-201-07](screenshots/run2/TC-201-07.png) [GIF](gifs/run2/TC-201-07.gif) [video](videos/run2/TC-201-07.webm) |
| TC-201-08 | PASS | PASS | 2.9 / 2.7 |  | [TC-201-08](screenshots/run2/TC-201-08.png) [GIF](gifs/run2/TC-201-08.gif) [video](videos/run2/TC-201-08.webm) |
| TC-201-09 | PASS | PASS | 2.8 / 2.9 |  | [TC-201-09](screenshots/run2/TC-201-09.png) [GIF](gifs/run2/TC-201-09.gif) [video](videos/run2/TC-201-09.webm) |
| TC-201-10 | PASS | PASS | 2.8 / 3.0 |  | [TC-201-10](screenshots/run2/TC-201-10.png) [GIF](gifs/run2/TC-201-10.gif) [video](videos/run2/TC-201-10.webm) |
| TC-201-11 | PASS | PASS | 3.1 / 3.1 |  | [TC-201-11-rejected](screenshots/run2/TC-201-11-rejected.png) [TC-201-11](screenshots/run2/TC-201-11.png) [GIF](gifs/run2/TC-201-11.gif) [video](videos/run2/TC-201-11.webm) |
| TC-201-12 | PASS | PASS | 5.5 / 9.2 |  | [TC-201-12-paused](screenshots/run2/TC-201-12-paused.png) [TC-201-12](screenshots/run2/TC-201-12.png) [GIF](gifs/run2/TC-201-12.gif) [video](videos/run2/TC-201-12.webm) |
| TC-201-13 | PASS | PASS | 19.2 / 22.6 | upload attempts while offline: 4 | [TC-201-13-failed](screenshots/run2/TC-201-13-failed.png) [TC-201-13](screenshots/run2/TC-201-13.png) [GIF](gifs/run2/TC-201-13.gif) [video](videos/run2/TC-201-13.webm) |
| TC-303-01 | PASS | PASS | 3.3 / 3.3 | TC-303-10 measured: {"event":"done","status":"COMPLETED","reason":null,"latencyMs":92,"firstTokenMs":28} | [TC-303-01](screenshots/run2/TC-303-01.png) [GIF](gifs/run2/TC-303-01+TC-303-10.gif) [video](videos/run2/TC-303-01+TC-303-10.webm) |
| TC-303-02 | PASS | PASS | 3.4 / 3.5 |  | [TC-303-02](screenshots/run2/TC-303-02.png) [GIF](gifs/run2/TC-303-02.gif) [video](videos/run2/TC-303-02.webm) |
| TC-303-03 | PASS | PASS | 3.5 / 3.6 |  | [TC-303-03](screenshots/run2/TC-303-03.png) [GIF](gifs/run2/TC-303-03.gif) [video](videos/run2/TC-303-03.webm) |
| TC-303-04 | PASS | PASS | 7.4 / 7.6 |  | [TC-303-04-chip1](screenshots/run2/TC-303-04-chip1.png) [TC-303-04-chip2](screenshots/run2/TC-303-04-chip2.png) [GIF](gifs/run2/TC-303-04.gif) [video](videos/run2/TC-303-04.webm) |
| TC-303-06 | PASS | PASS | 3.8 / 3.9 |  | [TC-303-06](screenshots/run2/TC-303-06.png) [GIF](gifs/run2/TC-303-06.gif) [video](videos/run2/TC-303-06.webm) |
| TC-303-07 | PASS | PASS | 3.9 / 4.0 |  | [TC-303-07](screenshots/run2/TC-303-07.png) [GIF](gifs/run2/TC-303-07+TC-303-08.gif) [video](videos/run2/TC-303-07+TC-303-08.webm) |
| TC-303-08 | PASS | PASS | 3.9 / 4.0 |  | [TC-303-08](screenshots/run2/TC-303-08.png) [GIF](gifs/run2/TC-303-07+TC-303-08.gif) [video](videos/run2/TC-303-07+TC-303-08.webm) |
| TC-303-09 | PASS | PASS | 3.3 / 3.4 | stored citation: {"index":1,"documentId":"01a19c6e-0d24-74f9-b6de-23e1af0aa1b3","fileName":"HopDong_ABC.pdf","page":2,"excerpt":"Điều 5. Thanh toán: khách hàng thanh toán 30% giá trị hợp đồng khi ký và 70% khi\nnghiệm thu.","removed":false} | [GIF](gifs/run2/TC-303-09.gif) [video](videos/run2/TC-303-09.webm) |
| TC-303-10 | PASS | PASS | 3.3 / 3.3 | TC-303-10 measured: {"event":"done","status":"COMPLETED","reason":null,"latencyMs":92,"firstTokenMs":28} | [GIF](gifs/run2/TC-303-01+TC-303-10.gif) [video](videos/run2/TC-303-01+TC-303-10.webm) |

Tổng: run1: 22/22 PASS · run2: 22/22 PASS — 22 TC tự động.
<!-- results:end -->

**Kết luận: 22/22 TC tự động PASS ở cả hai lượt chạy, không retry, không flaky.** 8/8 AC có ít nhất một TC PASS; AC-303.2 mới chỉ có phần tự động (TC-303-04), phần đo trên LLM thật (TC-303-05) còn mở.

## Các lần chạy trước khi đạt — và vì sao FAIL

Trước hai lượt chính thức, bộ test đã chạy 6 lần. Mỗi FAIL được điều tra tới nguyên nhân trước khi sửa — **không sửa test cho xanh**: với mỗi FAIL, câu hỏi đầu tiên là "sản phẩm sai hay phép đo sai?", và câu trả lời được chứng minh bằng dữ liệu (log, ảnh chụp, timeline request), không đoán.

| Lần | Kết quả | FAIL | Nguyên nhân (đã chứng minh) | Phiếu |
|---|---|---|---|---|
| 1 | 7 PASS · 2 FAIL · 10 bỏ qua (serial) | TC-201-05 "4 upload song song > 3" · TC-303-06 `Protocol error (Network.getResponseBody)` | Bộ đếm request của Playwright trễ một sự kiện · Playwright không đọc được body SSE đang stream | HD-1, HD-4 |
| 2 | 7 PASS · 2 FAIL | TC-201-05 vẫn "4" (đếm trong trang, theo `loadend`) · TC-303-06 không thấy tiêu đề "…trong **2** tài liệu…" | App resolve upload ở `onload`, `.finally → pump` mở file kế **trước** `loadend` của file cũ — sản phẩm đúng (≤ 3), phép đo sai · Ảnh chụp: app ghi "…trong **14** tài liệu…": kỳ vọng của TC sai tiền điều kiện | HD-1, TD-1 |
| 3 | 15 PASS · 2 FAIL · 2 bỏ qua | TC-201-13 "2 dòng Lon_8MB_b.pdf" · TC-303-06 "25" ≠ "26" | Timeline: server đã lưu file 8 MB ở ms 444 dù trình duyệt "mất mạng" ở ms 66 — throttle của DevTools chỉ giả lập, byte vẫn tới server · N = số tài liệu **Sẵn sàng** (25), không phải tổng kho (26, có 1 file Lỗi) | HD-2, TD-1 |
| 4 | 18 PASS · 1 FAIL | TC-303-09 `excerpt` không chứa "Thanh toán" | Excerpt là chữ PDF nguyên văn, khoảng trắng là U+00A0 (no-break space) của PDF — so khớp từng byte sai | TD-2 |
| 5 | 0 PASS · 2 FAIL · 17 bỏ qua | Cả hai test đầu: không có `#login-member` | Ảnh chụp: cổng :5173 đang là dev server của **một dự án khác**; `reuseExistingServer: true` đã dùng nhầm nó | HD-3 |
| 6 = run1 | **19 PASS** | — | | |
| 7 = run2 | **19 PASS** | — | | |

**Lỗi sản phẩm tìm thấy: 0** trong phạm vi AC. **1 quan sát** ngoài AC cần PO quyết định (OBS-1 — mất kết nối *sau* khi server đã lưu file).

## Số đo phi chức năng

| Chỉ số | Ngưỡng | Đo được | Ghi chú |
|---|---|---|---|
| TC-201-04 · file 49,5 MB tới "Sẵn sàng" | ≤ 300 s (NFR-03) | 5,0 s (cả hai lượt) | Môi trường cục bộ, mạng localhost; throttle 4 MB/s chỉ làm chậm phần hiển thị (HD-2) nên con số **lạc quan** — số đo có ý nghĩa phải lấy trên staging |
| TC-303-10 · tổng thời gian trả lời | ≤ 30 000 ms (NFR-01) | 94 ms · 89 ms | LLM giả lập → chỉ chứng minh đường đo (`latencyMs` từ server, ADR-16) hoạt động, **không** chứng minh NFR-01 với LLM thật |
| TC-303-10 · phần đầu câu trả lời | ≤ 5 000 ms (NFR-02) | 32 ms · 26 ms | Như trên |
| TC-201-05 · upload song song tối đa | ≤ 3 | 3 | Đếm trong trang ở mức XHR, kết thúc tính tại `readyState 4` |
| TC-201-13 · số lần gửi khi mất mạng | 1 + 3 lần thử | 4 | |

## Chưa phủ / rủi ro còn lại

- **TC-303-05** (≥ 27/30 trích dẫn đúng trang với LLM thật, LG-05) — cần staging + người chấm; giữ trạng thái *chưa chạy*, không tính là PASS.
- Chỉ Chromium. Edge / Chrome bản công ty (PQ-004) chạy bằng `E2E_STACK=compose` trên staging.
- OBS-1: mất kết nối sau khi server đã nhận file → hàng đợi báo "Tải lên thất bại" trong khi kho đã có file "Sẵn sàng". AC-201.4 không nói tới trường hợp này. Đề xuất TC mới sau khi PO quyết định hành vi mong muốn.
- Số đo NFR trên môi trường cục bộ không thay cho đo trên staging (test-plan §6, R3).
