Đã đọc AC, hợp đồng D4, chuỗi `vi.ts` và các tài khoản test. Bên dưới là bảng test case. Tôi không ghi file nào.

---

## US-204 · Gỡ tài liệu

Tiền điều kiện thêm:
- `member` đã tải lên `GoBo_Member_A.pdf`. Tài liệu này có cụm riêng "mã dự án ZEPHYR-204", không tài liệu nào khác chứa cụm này.
- `member2` đã tải lên `GoBo_Member2_B.pdf`.
- Cả hai file ở trạng thái "Sẵn sàng".
- Tài khoản test: `member`, `member2`, `lead`, `manager`, `outsider` (`e2e_server.py`).

| TC | AC | H | Bước | PASS khi (ghi trước) | FAIL khi |
|---|---|---|---|---|---|
| TC-204-01 | AC-204.1 | H | Đăng nhập `member`, mở menu "Tuỳ chọn cho GoBo_Member_A.pdf" | Menu có mục "Gỡ khỏi kho" | Không có mục này |
| TC-204-02 | AC-204.1 | N | Đăng nhập `member`, mở menu của `GoBo_Member2_B.pdf` (người khác tải lên) | Menu **không có** "Gỡ khỏi kho" (không tồn tại trong DOM, không chỉ bị disabled) | Mục hiện ra hoặc hiện ở dạng disabled |
| TC-204-03 | AC-204.1 | V | Đăng nhập `lead`, mở menu của `GoBo_Member_A.pdf` và `GoBo_Member2_B.pdf` | Menu của **cả 2** tài liệu có "Gỡ khỏi kho" | Thiếu ở ít nhất 1 tài liệu |
| TC-204-04 | AC-204.1 | V | Đăng nhập `manager`, mở menu của `GoBo_Member_A.pdf` | Không có "Gỡ khỏi kho" (PD-02 chỉ cho người tải lên hoặc LEAD) | Có mục này |
| TC-204-05 | AC-204.2 | H | `member` chọn "Gỡ khỏi kho" trên `GoBo_Member_A.pdf` | Dialog có tiêu đề "Gỡ tài liệu?" và nội dung đúng từng ký tự: "“GoBo_Member_A.pdf” sẽ không còn được dùng cho câu trả lời mới của cả đội. Thao tác này không hoàn tác được." Có 2 nút "Huỷ" và "Gỡ tài liệu". `document.activeElement` là nút "Huỷ" | Thiếu câu "cả đội", sai tên file, hoặc focus nằm ở "Gỡ tài liệu" hay ở chỗ khác |
| TC-204-06 | AC-204.2 | N | Mở dialog như TC-204-05, nhấn **Enter** ngay | Dialog đóng; **không có** `DELETE /documents/{id}`; tài liệu vẫn "Sẵn sàng" | Tài liệu bị gỡ (Enter kích hoạt nút xác nhận) |
| TC-204-07 | AC-204.2 | N | Mở dialog, nhấn **Esc**. Mở lại, bấm "Huỷ" | Cả hai lần dialog đều đóng, không có request DELETE, focus quay về nút menu ⋯ của tài liệu | Có request DELETE hoặc focus bị mất |
| TC-204-08 | AC-204.2 | P | Chạy axe trên dialog đang mở; dùng Tab/Shift+Tab | 0 lỗi serious/critical; focus bị giữ trong dialog (Tab từ nút cuối quay về "Huỷ"); dialog có `role="dialog"` hoặc `alertdialog` và `aria-labelledby` trỏ tới "Gỡ tài liệu?" | Có lỗi axe hoặc focus thoát ra trang nền |
| TC-204-09 | AC-204.3 | H | `member` xác nhận gỡ `GoBo_Member_A.pdf`, sau đó hỏi 10 câu chỉ trả lời được bằng nội dung riêng của file (ví dụ "Mã dự án ZEPHYR-204 có ngân sách bao nhiêu?" và 9 câu khác do fixture định nghĩa) | Toast "Đã gỡ “GoBo_Member_A.pdf”"; dòng biến khỏi kho ≤ 2 s (optimistic); `DELETE` trả **202**; **0/10** câu trả lời có mục Nguồn chứa `GoBo_Member_A.pdf`, và mỗi câu là thẻ "Không tìm thấy thông tin này trong N tài liệu hiện có" với N đọc từ kho (TD-1) | ≥ 1 câu trích từ file đã gỡ, hoặc vẫn còn dòng trong kho |
| TC-204-10 | AC-204.3 | V | Trước khi gỡ: hỏi "Mã dự án ZEPHYR-204 là gì?" và thấy chip trích từ `GoBo_Member_A.pdf`. Gỡ file trong **cùng hội thoại**, rồi bấm lại chip cũ (EC-15) | Chip bị gạch và có nhãn kết thúc bằng " (tài liệu đã được gỡ)", mục Nguồn có tag "(đã gỡ)". Bấm chip thì **không** mở PDF mà hiện "Tài liệu này vừa được gỡ khỏi kho." | Chip vẫn mở được trang PDF hoặc không có dấu hiệu đã gỡ |
| TC-204-11 | AC-204.3 | R | Hai phiên `member` và `lead` cùng mở kho. `lead` gỡ `GoBo_Member2_B.pdf` trước, sau đó `member2` (phiên đang mở, chưa làm mới) xác nhận gỡ cùng file | Lần gỡ thứ 2 nhận **404 DOC_NOT_FOUND**; FE hiện "Tài liệu này đã được gỡ khỏi kho." và làm mới danh sách, file không còn trong kho; không có lỗi 500 | Lỗi 500, file "sống lại" trong danh sách, hoặc hiện toast thành công giả |
| TC-204-12 | AC-204.3 | R | Giả lập `DELETE` trả **500** một lần (route intercept) khi `member` gỡ `GoBo_Member_A2.pdf` | Optimistic update được hoàn tác: dòng hiện lại ở trạng thái "Sẵn sàng"; toast "Đã có lỗi xảy ra. Vui lòng thử lại."; không có toast "Đã gỡ…" | Dòng biến mất dù server chưa gỡ |
| TC-204-13 | AC-204.4 | H | **Integration, đồng hồ giả:** gỡ `GoBo_Purge_C.pdf`, chạy job `purge_document` | Object không còn trong storage (`storage.head` → không tồn tại, **mọi phiên bản**, ADR-14); 0 dòng `text_chunk` và `document_page` của `document_id`; dòng `document` vẫn còn với `status='REMOVED'` và `purged_at` khác NULL; `purged_at − removed_at ≤ 24 h` | Còn object hay phiên bản cũ, còn chunk, hoặc mất tombstone |
| TC-204-14 | AC-204.4 | B | **Integration:** đặt đồng hồ `removed_at + 20 h` khi job chưa chạy được (storage lỗi), rồi `+19 h 59 m` | Ở 20 h: metric quá hạn ≥ 1 và cảnh báo SEC-06 được bắn. Ở 19 h 59 m: không có cảnh báo | Không có cảnh báo ở 20 h, hoặc cảnh báo sớm |
| TC-204-15 | AC-204.4 | R | **Integration:** `storage.delete` lỗi 4 lần rồi thành công ở lần thứ 5. Một kịch bản khác lỗi cả 6 lần | Kịch bản 1: purge xong ở lần thử 5, `purged_at` có giá trị. Kịch bản 2: dừng sau đúng 5 lần, `purged_at` vẫn NULL, metric quá hạn bắt được (cùng lượt với TC-204-14) | Thử quá 5 lần, hoặc ghi `purged_at` khi chưa xoá được |
| TC-204-16 | AC-204.4 | P | **Thủ công trên staging (MinIO thật có bật versioning):** gỡ `GoBo_Staging_D.pdf`, chờ ≤ 24 h | `mc ls --versions` không còn phiên bản nào; Loki có `document_purged {document_id}`; log và sự kiện **không** chứa tên file hay nội dung (TC-08) | Còn phiên bản hoặc log lộ nội dung |
| TC-204-17 | AC-204.5 | N | Gọi API trực tiếp bằng phiên `member2` (có CSRF hợp lệ): `DELETE /api/v1/documents/{id của GoBo_Member_A.pdf}` | **403**, `code=FORBIDDEN` (problem+json); sau đó `GET /documents` vẫn có file ở trạng thái "Sẵn sàng"; không có dòng audit `remove`, không có job purge | Mã 2xx, 404 hoặc 500, hoặc tài liệu bị đổi trạng thái |
| TC-204-18 | AC-204.5 | N | Gọi như TC-204-17 bằng phiên `outsider` (không có vai trò BD), và bằng request không có phiên | `outsider` nhận **403** `FORBIDDEN_ROLE`; không có phiên nhận **401**; tài liệu không đổi | Bất kỳ mã 2xx nào |
| TC-204-19 | AC-204.5 | V | Gọi API bằng `lead` trên file của `member2`. Kiểm tra sự kiện `document_removed` | **202**; sự kiện có đúng 2 props `role="lead"` và `doc_age_days` (số nguyên ≥ 0), không có trường nào khác | Bị 403, hoặc sự kiện có thêm trường (tên file hay nội dung) |

### Ma trận AC ↔ TC

| AC | TC | Số TC | Heuristic phủ |
|---|---|---|---|
| AC-204.1 | TC-204-01 → 04 | 4 | H, N, V |
| AC-204.2 | TC-204-05 → 08 | 4 | H, N, P |
| AC-204.3 | TC-204-09 → 12 | 4 | H, V, R |
| AC-204.4 | TC-204-13 → 16 | 4 | H, B, R, P |
| AC-204.5 | TC-204-17 → 19 | 3 | N, V |

Tổng cộng 19 TC. 2 TC dùng đồng hồ giả hoặc lỗi storage giả ở mức integration (TC-204-13, 14, 15 chạy cùng nhóm này). 1 TC chạy thủ công trên staging (TC-204-16). Các TC còn lại có thể làm E2E Playwright hoặc gọi API.

### AC đã rà và câu hỏi mở

1. **AC-204.1 và vai trò `manager`:** PD-02 chỉ nói "người tải lên hoặc LEAD". TC-204-04 đang giả định Quản lý **không** được gỡ. PQ-002 vẫn chặn story này, nên cần PO xác nhận.
2. **AC-204.3, nguồn của "10 câu hỏi kiểm thử":** AC không nói bộ câu nằm ở đâu. Tôi đề xuất fixture riêng gồm 10 câu gắn với `GoBo_Member_A.pdf`. Với LLM giả lập, kết quả "0/10" chủ yếu chứng minh tầng retrieval đã loại tài liệu. Muốn đo trên LLM thật thì cần thêm một lượt thủ công trên staging.
3. **AC-204.4, "24 giờ":** không thể đo thật trong E2E cục bộ, vì `e2e_server.py` không chạy job worker. Vì vậy TC-204-13 đến 15 dùng đồng hồ giả ở mức integration. Ngưỡng cảnh báo 20 h lấy từ T204.3, không có trong AC.
4. **TC-204-12 (DELETE lỗi 500):** AC không đặc tả hành vi này. Nó suy ra từ chuỗi "optimistic update" trong T204.4. Nếu PO coi đây là ngoài phạm vi thì chuyển TC này sang TD.
5. **Dữ liệu mới cần thêm vào `e2e/fixtures/build_fixtures.py`:** `GoBo_Member_A.pdf`, `GoBo_Member_A2.pdf`, `GoBo_Member2_B.pdf`, `GoBo_Purge_C.pdf`, `GoBo_Staging_D.pdf` và bộ 10 câu hỏi về ZEPHYR-204. Tên các file này không trùng với TC của US-201 và US-303.

Muốn ghi vào `docs/test-cases.md` thì gọi `/plan-tests US-204`.