# Test case: US-204 · Gỡ tài liệu

Tôi chỉ in kết quả ra đây, không ghi file nào (`docs/test-cases.md` và `e2e/fixtures/build_fixtures.py` không đổi). Kỳ vọng được ghi trước khi chạy, và mọi chuỗi giao diện lấy nguyên văn từ `web/src/i18n/vi.ts`.

**Tiền điều kiện thêm:** dùng app test (`backend/tests/e2e_server.py`) với các tài khoản `member`, `member2`, `lead`, `manager`, `outsider`. Mỗi TC có file riêng, tiền tố `G204_`, vì kho dùng chung cho mọi TC.

| TC | AC | H | Bước | PASS khi (ghi trước) | FAIL khi |
|---|---|---|---|---|---|
| TC-204-01 | AC-204.1 | H | `member` tải `G204_01_member.pdf` → "Sẵn sàng" → mở menu ⋯ của dòng đó | Menu có mục "Gỡ khỏi kho" | Không có mục |
| TC-204-02 | AC-204.1 | N | `member2` đăng nhập, mở menu ⋯ của `G204_01_member.pdf` | Menu **không có** "Gỡ khỏi kho" (không hiện, không chỉ bị mờ) | Có mục, kể cả dạng disabled |
| TC-204-03 | AC-204.1 | V | `lead` mở menu ⋯ của `G204_01_member.pdf` (do người khác tải) | Có "Gỡ khỏi kho" (PD-02) | Không có mục |
| TC-204-04 | AC-204.1 | V | `member2` tải `G204_04_member2.pdf`, mở menu của chính file đó | Có "Gỡ khỏi kho" (chủ của file nào thì thấy trên file đó) | Không có mục |
| TC-204-05 | AC-204.1 | N | `manager` mở menu ⋯ của `G204_01_member.pdf` | Không có "Gỡ khỏi kho" (manager không phải người tải, không phải LEAD) ‹xem câu hỏi Q1› | Có mục |
| TC-204-06 | AC-204.2 | H | `member` chọn "Gỡ khỏi kho" trên `G204_06.pdf` | Hộp thoại có tiêu đề "Gỡ tài liệu?", nội dung "“G204_06.pdf” sẽ không còn được dùng cho câu trả lời mới của cả đội. Thao tác này không hoàn tác được.", 2 nút "Huỷ" / "Gỡ tài liệu"; `document.activeElement` là nút "Huỷ" | Thiếu chữ "cả đội", sai tên file, hoặc focus không ở "Huỷ" |
| TC-204-07 | AC-204.2 | N | Mở hộp thoại của TC-204-06 rồi nhấn ngay **Enter** | Hộp thoại đóng; **không có** `DELETE /api/v1/documents/{id}`; dòng `G204_06.pdf` vẫn "Sẵn sàng" | Tài liệu bị gỡ (Enter rơi vào nút xác nhận) |
| TC-204-08 | AC-204.2 | N | Mở lại hộp thoại → nhấn **Esc**; mở lại lần nữa → bấm "Huỷ" | Cả 2 lần hộp thoại đóng, 0 request `DELETE`, focus quay về nút ⋯ của dòng | Có request gỡ, hoặc focus bị mất |
| TC-204-09 | AC-204.2 | P | (cùng lượt với TC-204-06) chạy axe trên hộp thoại; Tab / Shift+Tab 4 lần | 0 lỗi serious/critical; `role="alertdialog"` hoặc `dialog` có `aria-modal="true"`; focus chỉ vòng giữa "Huỷ" và "Gỡ tài liệu" | Có lỗi axe, hoặc focus thoát ra ngoài hộp thoại |
| TC-204-10 | AC-204.3 | H | `G204_10_Zeta.pdf` chứa nội dung riêng (vd. "Mã dự án ZETA-204, đơn giá 7.204.000 đ/tháng"); xác nhận gỡ | Toast "Đã gỡ “G204_10_Zeta.pdf”"; dòng biến mất khỏi kho ≤ 1 s, không cần tải lại trang (optimistic); API trả `202` | Dòng còn đó, sai toast, hoặc khác 202 |
| TC-204-11 | AC-204.3 | H | Ngay sau TC-204-10, hỏi 10 câu chỉ trả lời được từ file đó (ZETA-204, đơn giá, thời hạn… dùng 10 câu cố định) | 0/10 câu trả lời có trích dẫn tới `G204_10_Zeta.pdf`; mỗi câu là câu trả lời từ tài liệu khác hoặc thẻ "Không tìm thấy thông tin này trong N tài liệu hiện có", với N đọc từ hệ thống (TD-1) | ≥ 1 câu trích file đã gỡ |
| TC-204-12 | AC-204.3 | V | Hỏi câu trích `G204_12.pdf` → có chip [1] → gỡ `G204_12.pdf` trong lúc hội thoại vẫn mở (EC-15) | Chip cũ được gạch, nhãn có " (tài liệu đã được gỡ)" / "(đã gỡ)"; bấm chip thì vùng nguồn hiện "Tài liệu này vừa được gỡ khỏi kho." và không tải PDF | Chip vẫn mở được trang của file đã gỡ |
| TC-204-13 | AC-204.3 | P | **Thủ công trên staging, LLM thật:** lặp TC-204-11 với retrieval thật | 0/10 (AC-005) | ≥ 1/10 |
| TC-204-14 | AC-204.4 | H | **Integration (fake clock):** gỡ `G204_14.pdf` → chạy job `purge_document` | `storage` không còn object; `text_chunk` và `document_page` của doc có 0 dòng; dòng `document` vẫn còn (tombstone) với `status='REMOVED'`, `purged_at` khác null | Còn object/chunk, hoặc mất tombstone |
| TC-204-15 | AC-204.4 | R | Integration: `storage.delete` lỗi 2 lần rồi thành công | Job thử lại theo lịch 1 → 5 phút; lần 3 thành công; `purged_at` có giá trị, tổng < 24 h | Job dừng hẳn sau lỗi đầu, hoặc thử quá 5 lần |
| TC-204-16 | AC-204.4 | B | Integration: doc gỡ lúc t0, purge luôn lỗi; đặt clock t0 + 19 h 59 m rồi t0 + 20 h 01 m | Gauge `documents_purge_overdue` = 0 rồi = 1 (cảnh báo trước hạn 24 h, SEC-06) | Sai giá trị ở một trong hai mốc |
| TC-204-17 | AC-204.4 | N | **Thủ công, MinIO bucket bật versioning (compose):** gỡ `G204_17.pdf` → purge → `mc ls --versions` | 0 phiên bản, 0 delete marker còn lại (ADR-14) | Còn phiên bản khôi phục được |
| TC-204-18 | AC-204.5 | N | `member2` gọi `DELETE /api/v1/documents/{id của G204_18_member.pdf}` | `403`, problem+json `code=FORBIDDEN`; tài liệu vẫn "Sẵn sàng"; không có audit `remove` | Trả 2xx, hoặc tài liệu bị gỡ |
| TC-204-19 | AC-204.5 | N | `outsider` (nhóm `grp-ke-toan`) gọi cùng API | `403`, `code=FORBIDDEN_ROLE` | Trả 2xx hoặc 404 (lộ việc tài liệu tồn tại) |
| TC-204-20 | AC-204.5 | N | `manager` gọi `DELETE` trên tài liệu của `member` | `403 FORBIDDEN` ‹Q1› | Trả 202 |
| TC-204-21 | AC-204.5 | B | `member` và `lead` cùng gửi `DELETE` một tài liệu `G204_21.pdf` (song song) | Đúng 1 lần `202`, lần còn lại `404 DOC_NOT_FOUND`; FE làm mới danh sách; chỉ 1 job purge, 1 dòng audit | 2 lần 202, 2 job, hoặc lỗi 500 |
| TC-204-22 | AC-204.5 | N | Gọi API không có cookie phiên | `401`, tài liệu không đổi | Trả 2xx hoặc 403 |

## Ma trận AC ↔ TC

| AC | TC | Số TC | Heuristic phủ |
|---|---|---|---|
| AC-204.1 | TC-204-01 → 05 | 5 | H, N, V |
| AC-204.2 | TC-204-06 → 09 | 4 | H, N, P |
| AC-204.3 | TC-204-10 → 13 | 4 | H, V, P |
| AC-204.4 | TC-204-14 → 17 | 4 | H, R, B, N |
| AC-204.5 | TC-204-18 → 22 | 5 | N, B |

Tổng 22 TC: 17 chạy tự động trên app test bằng Playwright/API, 3 là integration với fake clock (TC-204-14, 15, 16), 2 làm thủ công (TC-204-13, 17).

## Những điểm cần biết khi rà AC

- **AC-204.4 không chạy được trên app test hiện tại.** `e2e_server.py` chỉ đăng ký handler cho `PROCESS_DOCUMENT`, nên job `purge_document` không bao giờ chạy. Vì vậy TC-204-14 → 16 phải là integration test, còn TC-204-17 cần stack compose có MinIO.
- **"Qua 24 giờ" không thể chờ thật.** Biên được đo bằng ngưỡng cảnh báo 20 h (`PURGE_ALERT_AFTER`) và lịch thử lại, cả hai với fake clock.
- **TC-204-12 (EC-15) và TC-204-21 (hai người cùng gỡ)** lấy từ mục "Trường hợp biên" của task, không có AC riêng. Tôi tạm gắn chúng vào AC-204.3 và AC-204.5.

## Câu hỏi mở

1. **Q1, role `manager` (PQ-002 chưa chốt):** AC-204.1 chỉ nói người tải lên hoặc Trưởng nhóm. Tôi giả định manager **không** được gỡ (TC-204-05, 20). Bạn xác nhận giúp?
2. AC-204.3 cần "10 câu hỏi kiểm thử", nhưng bộ câu chưa có trong đặc tả. Bạn có muốn dùng bộ câu cố định của TC-204-11 làm chuẩn không?
3. Có thêm TC kiểm sự kiện `document_removed` không? Nó chỉ được mang `role` và `doc_age_days`, không chứa tên file (TC-08). Sự kiện này không thuộc AC nào nên tôi chưa đưa vào.

Nếu bạn muốn ghi bảng này vào `docs/test-cases.md` và thêm fixture `G204_*`, nói tôi để làm tiếp.