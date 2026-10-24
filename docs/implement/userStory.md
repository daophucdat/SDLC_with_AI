# User Stories — Chat với tài liệu (MVP)

| Thuộc tính | Giá trị |
|---|---|
| Tài liệu | US-BACKLOG-001 |
| Phiên bản | 0.1 · Draft |
| Ngày | 2026-10-21 |
| Nguồn | [PRD v0.2 §3](../02-requirements/PRD.md) (22 user story), [Use case spec](../02-requirements/UseCase_Specification.md), [SAD v0.1](../03-design/SAD.md), [Blueprint v1.1](../04-design/Blueprint_SDD.md), [UI/UX](../04-design/UI_UX_design/index.html) |
| Dùng cho | Product backlog, sprint planning, nghiệm thu; kế hoạch triển khai ở [implement_plan.md](implement_plan.md) |

**Quy ước**
- **ID story giữ nguyên theo PRD** (US-101 → US-402). Story kỹ thuật dùng tiền tố **EN-** (enabler), suy ra từ SAD và Blueprint.
- **Ưu tiên:** P0 = bắt buộc để ra mắt · P1 = nên có · P2 = có thể có (PRD §3).
- **Story point** (thang 1, 2, 3, 5, 8) là `[Đề xuất]`, cần đội phát triển ước lượng lại trong buổi planning.
- **AC** viết theo Given-When-Then. AC của P0 lấy từ PRD; AC của P1/P2 chuyển từ PRD §3.6. Ngưỡng có nhãn `[PRD-new]` vẫn chờ PQ-005.
- Story nào bị chặn bởi một câu hỏi mở thì ghi ở dòng **Chặn bởi**.

---

## 0. Tổng quan backlog

| Epic | Mô tả | Story | P0 | P1 | P2 | Điểm |
|---|---|---|---|---|---|---|
| E1. Truy cập | Chỉ thành viên BD được vào | US-101 → 103 | 2 | 1 | 0 | 10 |
| E2. Kho tài liệu | Đưa vào, theo dõi, xem, gỡ PDF | US-201 → 206 | 2 | 3 | 1 | 20 |
| E3. Hỏi đáp có dẫn nguồn | Hỏi, trả lời tổng hợp, trích dẫn | US-301 → 311 | 4 | 5 | 2 | 47 |
| E4. Đo lường giá trị | Số liệu, nghiệm thu | US-401 → 402 | 0 | 1 | 1 | 10 |
| EN. Enabler kỹ thuật | Nền tảng, AI, bảo mật, vận hành, kiểm thử | EN-01 → 12 | — | — | — | 63 |
| **Tổng** | | **34** | **8** | **10** | **4** | **150** |

**Definition of Ready (DoR)** — một story được đưa vào sprint khi:
1. Có AC dạng Given-When-Then kiểm chứng được.
2. Đã ước lượng điểm.
3. Không còn câu hỏi mở nào chặn nó (hoặc đã có quyết định tạm thời được ghi lại).
4. Có thiết kế UI trong [UI/UX design](../04-design/UI_UX_design/index.html), nếu story có giao diện.
5. Đã xác định phụ thuộc (story / enabler khác).

**Definition of Done (DoD)** — một story được coi là xong khi:
1. Mọi AC đạt, có test tự động (unit / integration / E2E phù hợp) chạy trong CI.
2. Code đã được review; CI xanh (lint, kiểm tra quy tắc import DR-1 → DR-5, test).
3. Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log hay sự kiện (QAS-06).
4. Giao diện đạt WCAG 2.1 AA (axe không có lỗi serious / critical) và dùng đúng design token.
5. Sự kiện phân tích liên quan (PRD §5.2) đã được ghi.
6. Đã deploy lên môi trường staging và PO / BA demo được.

---

## E1. Truy cập

### US-101 · Đăng nhập bằng tài khoản công ty · **P0** · 5 điểm
> Là **chuyên viên BD**, tôi muốn đăng nhập bằng tài khoản công ty do IT cấp, để không phải nhớ thêm mật khẩu riêng.

- **AC-101.1** — *Given* tôi là thành viên BD đã được IT cấp quyền, *When* tôi mở đường dẫn và đăng nhập bằng tài khoản công ty, *Then* tôi vào màn hình làm việc trong ≤ 5 giây và thấy tên của mình.
- **AC-101.2** — *Given* tôi đã đăng nhập, *When* tôi đóng tab rồi mở lại khi phiên còn hiệu lực, *Then* tôi không phải đăng nhập lại.
- **AC-101.3** — *Given* hệ thống tài khoản công ty không phản hồi, *When* tôi đăng nhập, *Then* tôi thấy thông báo "chưa đăng nhập được" kèm nút thử lại.

| Truy vết | BR-012 · UCD-01, UCD-02 · SEC-01 · LG-10 · màn hình `login.html` |
|---|---|
| Phụ thuộc | EN-02 (OIDC client, secrets) |
| Chặn bởi | DEP-002 (IdP công ty, ánh xạ nhóm → vai trò) |

### US-102 · Từ chối người không thuộc đội BD · **P0** · 3 điểm
> Là **quản lý**, tôi muốn người không thuộc đội BD bị từ chối truy cập, để tài liệu nội bộ không bị lộ.

- **AC-102.1** — *Given* một tài khoản công ty không thuộc nhóm BD được cấp quyền, *When* người đó đăng nhập, *Then* họ thấy "Bạn chưa được cấp quyền dùng công cụ này. Liên hệ trưởng nhóm BD." và không thấy tên hay số lượng tài liệu.
- **AC-102.2** — *Given* một người chưa đăng nhập, *When* họ gọi trực tiếp API hoặc đường dẫn tài liệu, *Then* yêu cầu bị từ chối (`401`/`403`).
- **AC-102.3** — *Given* bộ ≥ 20 ca truy cập trái phép, *When* QA chạy, *Then* 100% bị từ chối (AC-012).

| Truy vết | BR-012, RUL-001 · UCD-02 · EC-18 · LG-10 |
|---|---|
| Phụ thuộc | US-101, EN-09 (audit log) |

### US-103 · Tự kết thúc phiên khi không hoạt động · **P1** · 2 điểm
> Là **chuyên viên BD**, tôi muốn phiên tự kết thúc sau 8 giờ không hoạt động, để máy để quên không mở sẵn tài liệu cho người khác.

- **AC-103.1** — *Given* phiên đã 8 giờ không có thao tác, *When* tôi thao tác tiếp, *Then* tôi được chuyển về đăng nhập.
- **AC-103.2** — *Given* tôi đang gõ dở một câu hỏi khi phiên hết hạn, *When* tôi đăng nhập lại, *Then* câu hỏi đang gõ vẫn còn (EC-17).
- **AC-103.3** — *Given* tôi đăng xuất, *When* phiên bị xoá, *Then* hội thoại của phiên cũng bị xoá (PD-04).

| Truy vết | SN-007 · UCD-03 · PD-04 · `[PRD-new]` 8 giờ chờ PQ-005 |
|---|---|
| Phụ thuộc | US-101 |

---

## E2. Kho tài liệu

### US-201 · Tải một hoặc nhiều file PDF · **P0** · 5 điểm
> Là **chuyên viên BD**, tôi muốn kéo-thả một hoặc nhiều file PDF vào sản phẩm, để các file đó trở thành nguồn cho câu trả lời.

- **AC-201.1** — *Given* tôi ở màn hình làm việc, *When* tôi thả 1 file PDF dạng văn bản ≤ 50 MB (hoặc chọn bằng nút "Tải tài liệu"), *Then* file xuất hiện trong danh sách với trạng thái "Đang tải lên" và % tiến độ.
- **AC-201.2** — *Given* tôi chọn đồng thời 10 file hợp lệ, *When* tôi thả vào, *Then* cả 10 file vào hàng đợi, mỗi file có trạng thái riêng.
- **AC-201.3** — *Given* một file không phải PDF hoặc > 50 MB, *When* tôi thả vào, *Then* file đó bị từ chối trước khi tải lên, kèm lý do đúng; các file hợp lệ khác vẫn được tải.
- **AC-201.4** — *Given* mất mạng khi đang tải, *When* có mạng lại, *Then* file tự tải tiếp (tối đa 3 lần thử); quá 3 lần thì báo lỗi kèm nút "Thử lại" (EC-04).

| Truy vết | BR-001 · UCD-04, UCD-05 · EC-04, EC-07, EC-08 · NFR-06 · REL-05 |
|---|---|
| Phụ thuộc | EN-02 (storage), EN-11 (component UploadDropzone, DocumentItem) |
| Chặn bởi | PQ-001 (kho chung) — tạm theo PD-01 |

### US-202 · Theo dõi trạng thái xử lý từng file · **P0** · 3 điểm
> Là **chuyên viên BD**, tôi muốn thấy trạng thái từng file (đang tải, đang xử lý, sẵn sàng, lỗi), để biết khi nào có thể hỏi về file đó.

- **AC-202.1** — *Given* một file 50 MB / 300 trang đã tải xong, *When* xử lý kết thúc, *Then* trạng thái chuyển "Sẵn sàng" chậm nhất 5 phút sau khi tải lên (AC-001) và file được dùng ngay cho câu hỏi tiếp theo.
- **AC-202.2** — *Given* một file đang "Đang xử lý", *When* tôi đặt câu hỏi, *Then* câu trả lời chỉ dùng file "Sẵn sàng" và có ghi chú "1 tài liệu đang được xử lý, chưa được dùng".
- **AC-202.3** — *Given* xử lý thất bại (mật khẩu, file hỏng), *When* trạng thái là "Lỗi", *Then* tôi thấy lý do bằng ngôn ngữ thường ngày và nút "Thử lại" (EC-09, EC-11).

| Truy vết | BR-001 · UCD-06, UCD-09 · NFR-03 · LG-07 |
|---|---|
| Phụ thuộc | EN-04 (pipeline xử lý) |

### US-203 · Xem và lọc danh sách tài liệu · **P1** · 3 điểm
> Là **chuyên viên BD**, tôi muốn xem danh sách tài liệu (tên, số trang, người tải, ngày tải), để biết câu trả lời dựa trên những tài liệu nào.

- **AC-203.1** — *Given* kho có N tài liệu, *When* tôi mở màn hình làm việc, *Then* danh sách hiển thị đủ N tài liệu với tên file, số trang, người tải, ngày tải (AC-004).
- **AC-203.2** — *Given* tôi gõ ≥ 2 ký tự vào ô lọc, *When* có tài liệu khớp, *Then* danh sách chỉ còn các tài liệu khớp; không có thì hiện "Không có tài liệu nào khớp" kèm nút xoá bộ lọc.

| Truy vết | BR-004 · UCD-10, UCD-14 |
|---|---|
| Phụ thuộc | US-201 |

### US-204 · Gỡ tài liệu · **P1** · 5 điểm
> Là **chuyên viên BD**, tôi muốn gỡ một tài liệu tôi đã tải lên, để tài liệu lỗi thời không còn được dùng trong câu trả lời mới.

- **AC-204.1** — *Given* tôi là người tải lên (hoặc là Trưởng nhóm BD), *When* tôi mở menu của tài liệu, *Then* có mục "Gỡ khỏi kho"; với người khác thì mục này không có (PD-02).
- **AC-204.2** — *Given* tôi chọn "Gỡ khỏi kho", *When* hộp xác nhận hiện ra, *Then* nó nêu rõ ảnh hưởng tới cả đội và focus mặc định ở "Huỷ".
- **AC-204.3** — *Given* tôi xác nhận gỡ, *When* hỏi 10 câu hỏi kiểm thử về nội dung riêng của tài liệu đó, *Then* 0/10 câu trả lời trích từ nó (AC-005).
- **AC-204.4** — *Given* tài liệu đã bị gỡ, *When* qua 24 giờ, *Then* file và nội dung đã bị xoá vĩnh viễn khỏi kho lưu trữ và chỉ mục (SEC-06).
- **AC-204.5** — *Given* người không có quyền gọi API gỡ, *When* yêu cầu đến máy chủ, *Then* bị từ chối `403`.

| Truy vết | BR-005, RUL-003 · UCD-11 → 13, UCD-15 · PD-02 · SEC-06 |
|---|---|
| Phụ thuộc | US-203, EN-09 (job purge) |
| Chặn bởi | PQ-002 (ai được gỡ) — tạm theo PD-02 |

### US-205 · Báo file không đọc được chữ · **P1** · 2 điểm
> Là **chuyên viên BD**, tôi muốn được báo khi PDF không có chữ đọc được (file scan), để không tưởng rằng file đó đã được tra cứu.

- **AC-205.1** — *Given* bộ 10 file PDF dạng ảnh scan, *When* tải lên, *Then* 10/10 có trạng thái "Không đọc được chữ" kèm giải thích (AC-006).
- **AC-205.2** — *Given* một file "Không đọc được chữ", *When* tôi đặt câu hỏi, *Then* file đó không xuất hiện trong trích dẫn.

| Truy vết | BR-006 · UCD-07 · EC-10 · ASM-003 |
|---|---|
| Phụ thuộc | EN-04 |

### US-206 · Cảnh báo file trùng · **P2** · 2 điểm
> Là **chuyên viên BD**, tôi muốn được cảnh báo khi tải lên một file trùng với file đã có, để kho không có bản trùng làm câu trả lời bị lặp.

- **AC-206.1** — *Given* một file có nội dung trùng 100% với tài liệu chưa gỡ, *When* tôi tải lên, *Then* hệ thống hỏi "File này đã có trong kho (tải lên ngày …). Vẫn tải?" trong 100% lần thử.
- **AC-206.2** — *Given* tôi chọn "Vẫn tải", *When* xác nhận, *Then* file được tải như bình thường.

| Truy vết | SN-006 · UCD-08 · EC-12 · `[PRD-new]` |
|---|---|
| Phụ thuộc | US-201 (tính mã băm nội dung) |

---

## E3. Hỏi đáp có dẫn nguồn

### US-301 · Hỏi bằng tiếng Việt hoặc tiếng Anh · **P0** · 3 điểm
> Là **chuyên viên BD**, tôi muốn gõ câu hỏi bằng tiếng Việt hoặc tiếng Anh như khi hỏi đồng nghiệp, để không phải học cú pháp tìm kiếm.

- **AC-301.1** — *Given* kho có ≥ 1 tài liệu "Sẵn sàng", *When* tôi gõ câu hỏi tiếng Việt và nhấn Enter, *Then* câu hỏi được gửi và câu trả lời bằng tiếng Việt bắt đầu hiện.
- **AC-301.2** — *Given* như trên, *When* tôi hỏi bằng tiếng Anh, *Then* câu trả lời bằng tiếng Anh.
- **AC-301.3** — *Given* ô câu hỏi trống hoặc chỉ có khoảng trắng, *When* tôi nhấn Enter, *Then* không có gì được gửi.
- **AC-301.4** — *Given* câu hỏi > 2.000 ký tự, *When* tôi gõ tiếp, *Then* bộ đếm chuyển màu cảnh báo và nút Gửi bị vô hiệu.
- **AC-301.5** — *Given* kho chưa có tài liệu "Sẵn sàng", *When* tôi mở màn hình, *Then* ô câu hỏi bị vô hiệu kèm lý do (EC-01, EC-03).

| Truy vết | BR-002 · UCD-16 · AC-002 |
|---|---|
| Phụ thuộc | EN-11 (QuestionComposer) |
| Chặn bởi | OQ-014 (ngôn ngữ) — tạm tiếng Việt + tiếng Anh |

### US-302 · Câu trả lời tổng hợp từ mọi tài liệu liên quan · **P0** · 8 điểm
> Là **chuyên viên BD**, tôi muốn câu trả lời tổng hợp thông tin từ tất cả tài liệu liên quan, để không bỏ sót thông tin nằm ở file khác.

- **AC-302.1** — *Given* thông tin cho một câu hỏi nằm ở 2 tài liệu khác nhau, *When* tôi hỏi, *Then* câu trả lời chứa thông tin từ cả 2 và có trích dẫn tới cả 2.
- **AC-302.2** — *Given* bộ 15 câu hỏi kiểm thử cần thông tin từ ≥ 2 tài liệu, *When* Trưởng nhóm BD chấm, *Then* ≥ 80% câu trả lời đúng và đủ (AC-003, LG-03).
- **AC-302.3** — *Given* một tài liệu đã bị gỡ, *When* tôi hỏi về nội dung chỉ có trong nó, *Then* câu trả lời không trích từ tài liệu đó (RUL-003).

| Truy vết | BR-003 · UCD-19 · ALG-2 · LG-03 |
|---|---|
| Phụ thuộc | EN-05 (truy xuất lai), EN-06 (LLM adapter), EN-10 (bộ câu hỏi kiểm thử) |
| Chặn bởi | **OQ-008** (được dùng LLM đám mây không) |

### US-303 · Mỗi ý có trích dẫn tài liệu và trang · **P0** · 5 điểm
> Là **chuyên viên BD**, tôi muốn mỗi ý trong câu trả lời có trích dẫn tên tài liệu và số trang, để kiểm chứng trước khi dùng với khách hàng.

- **AC-303.1** — *Given* câu trả lời có thông tin, *When* nó hiển thị xong, *Then* mỗi đoạn có ≥ 1 trích dẫn `[n]`, và cuối câu trả lời có danh sách "Tên tài liệu — trang X".
- **AC-303.2** — *Given* mẫu 30 trích dẫn ngẫu nhiên, *When* QA mở từng trang được trích, *Then* ≥ 90% trang chứa đúng thông tin (AC-007, LG-05).
- **AC-303.3** — *Given* LLM trả về câu trả lời không có trích dẫn, hoặc trích dẫn số không có trong ngữ cảnh, *When* máy chủ kiểm tra (ALG-3), *Then* câu trả lời bị chuyển thành "không tìm thấy" (EC-14).
- **AC-303.4** — *Given* một câu trả lời COMPLETED, *When* kiểm tra dữ liệu lưu, *Then* vị trí nguồn (tài liệu, trang, đoạn trích) lấy từ chỉ mục, không lấy từ chữ do LLM viết.

| Truy vết | BR-007 · UCD-20 · ALG-3 · QAS-07 · LG-05 |
|---|---|
| Phụ thuộc | US-302 |

### US-304 · Báo rõ "không tìm thấy" · **P0** · 5 điểm
> Là **chuyên viên BD**, tôi muốn được báo rõ "không tìm thấy" khi tài liệu không có thông tin, để không dùng nhầm thông tin bịa.

- **AC-304.1** — *Given* thông tin không có trong tài liệu "Sẵn sàng" nào, *When* tôi hỏi, *Then* tôi nhận "Không tìm thấy thông tin này trong N tài liệu hiện có" kèm gợi ý diễn đạt lại hoặc tải thêm tài liệu.
- **AC-304.2** — *Given* bộ 10 câu hỏi kiểm thử không có đáp án trong tài liệu, *When* QA chạy, *Then* ≥ 9 câu nhận "không tìm thấy" (AC-008, LG-04).
- **AC-304.3** — *Given* trạng thái "không tìm thấy", *When* hiển thị, *Then* dùng giao diện trung tính (không phải màu lỗi) và không chứa thông tin ngoài tài liệu (RUL-002).
- **AC-304.4** — *Given* không có đoạn nào vượt ngưỡng `τ` và tìm kiếm toàn văn rỗng, *When* xử lý câu hỏi, *Then* hệ thống trả "không tìm thấy" mà **không** gọi LLM (ALG-2).

| Truy vết | BR-008, RUL-002 · UCD-21 · LG-04 · TQ-07 |
|---|---|
| Phụ thuộc | EN-05, EN-10 (hiệu chỉnh `τ`) |

### US-305 · Mở đúng trang nguồn · **P1** · 5 điểm
> Là **chuyên viên BD**, tôi muốn bấm vào trích dẫn để mở đúng trang PDF cạnh khung chat, để kiểm chứng mà không rời cuộc hội thoại.

- **AC-305.1** — *Given* câu trả lời có trích dẫn `[1]`, *When* tôi bấm `[1]`, *Then* vùng nguồn mở đúng tài liệu, đúng trang, đoạn liên quan được tô sáng, trong ≤ 2 giây ở p95 với file ≤ 50 MB (NFR-05).
- **AC-305.2** — *Given* vùng nguồn đang mở, *When* tôi bấm `[2]`, *Then* vùng nguồn chuyển sang nguồn mới, không mở cửa sổ mới.
- **AC-305.3** — *Given* tài liệu của trích dẫn đã bị gỡ, *When* tôi xem câu trả lời, *Then* trích dẫn bị gạch, có chú thích "Tài liệu đã được gỡ" và không mở được (EC-15).

| Truy vết | BR-007, SN-005 · UCD-22 · NFR-05 |
|---|---|
| Phụ thuộc | US-303; endpoint file có Range (SAD §2.4) |

### US-306 · Câu trả lời hiện dần · **P1** · 5 điểm
> Là **chuyên viên BD**, tôi muốn thấy câu trả lời hiện dần trong lúc được soạn, để không phải nhìn màn hình trống khi chờ.

- **AC-306.1** — *Given* tôi đã gửi câu hỏi, *When* LLM bắt đầu trả lời, *Then* phần đầu tiên hiển thị trong ≤ 5 giây ở p95 (NFR-02).
- **AC-306.2** — *Given* câu trả lời đã hiện một phần, *When* kiểm tra cuối cùng thấy trích dẫn không hợp lệ, *Then* toàn bộ nội dung được thay bằng "không tìm thấy" kèm giải thích (TQ-01).
- **AC-306.3** — *Given* mất kết nối khi đang nhận, *When* luồng bị ngắt, *Then* phần đã nhận vẫn hiển thị, gắn nhãn "chưa hoàn chỉnh" và có nút "Hỏi lại" (EC-05).

| Truy vết | BR-009 · UCD-19 · NFR-02 · SAD ADR-11 (SSE) |
|---|---|
| Phụ thuộc | US-302 |
| Chặn bởi | **TQ-01** (giữ cách "hiện dần rồi thay"?), PQ-006 (BR-009 thành Must?) |

### US-307 · Sao chép câu trả lời kèm nguồn · **P1** · 2 điểm
> Là **chuyên viên BD**, tôi muốn sao chép câu trả lời kèm danh sách nguồn, để dán vào email hoặc tài liệu đề xuất.

- **AC-307.1** — *Given* một câu trả lời hoàn tất, *When* tôi bấm "Sao chép kèm nguồn", *Then* clipboard chứa câu trả lời và danh sách "Tên tài liệu — trang X".
- **AC-307.2** — *Given* trình duyệt chặn ghi clipboard, *When* tôi bấm sao chép, *Then* tôi được báo hãy chọn và sao chép thủ công.

| Truy vết | SN-001 · UCD-24 · sự kiện `answer_copied` |
|---|---|
| Phụ thuộc | US-303 |

### US-308 · Xem lại hội thoại hiện tại · **P2** · 3 điểm
> Là **chuyên viên BD**, tôi muốn xem lại các câu hỏi và câu trả lời trong cuộc hội thoại hiện tại, để không phải hỏi lại.

- **AC-308.1** — *Given* tôi đã hỏi 10 lượt trong phiên, *When* tôi cuộn lại hoặc tải lại trang, *Then* cả 10 cặp câu hỏi và câu trả lời đều xem lại được (AC-010).
- **AC-308.2** — *Given* tôi đăng xuất rồi đăng nhập lại, *When* mở màn hình làm việc, *Then* hội thoại cũ không còn (PD-04).

| Truy vết | BR-010 · UCD-18 · PD-04 |
|---|---|
| Chặn bởi | PQ-003 (có lưu lịch sử qua phiên không) |

### US-309 · Đánh giá câu trả lời · **P1** · 3 điểm
> Là **trưởng nhóm BD**, tôi muốn thành viên đánh giá hữu ích / chưa tốt cho từng câu trả lời, để phát hiện sớm loại câu hỏi sản phẩm trả lời kém.

- **AC-309.1** — *Given* một câu trả lời hoàn tất, *When* tôi bấm 👍, *Then* phản hồi được ghi và tôi thấy lời cảm ơn; sinh đúng 1 sự kiện `answer_feedback_submitted`.
- **AC-309.2** — *Given* tôi bấm 👎, *When* danh sách lý do hiện ra (Sai thông tin / Thiếu ý / Sai nguồn / Khác), *Then* chọn một lý do sẽ gửi phản hồi kèm lý do.

| Truy vết | PD-03 · KR3.2 · UCD-25 |
|---|---|
| Phụ thuộc | EN-08 (sự kiện) |

### US-310 · Dừng câu trả lời đang soạn · **P1** · 3 điểm
> Là **chuyên viên BD**, tôi muốn dừng một câu trả lời đang soạn, để hỏi lại ngay khi nhận ra mình hỏi sai.

- **AC-310.1** — *Given* câu trả lời đang hiện dần, *When* tôi bấm "Dừng", *Then* câu trả lời ngừng trong ≤ 1 giây, gắn nhãn "Đã dừng", ô câu hỏi dùng được ngay.
- **AC-310.2** — *Given* tôi đã bấm Dừng, *When* kiểm tra phía máy chủ, *Then* lời gọi LLM đã bị huỷ (không tốn thêm token) và sinh sự kiện `answer_stopped`.

| Truy vết | BR-009 · UCD-23 · SAD §3.2.1 bước 9 |
|---|---|
| Phụ thuộc | US-306 |

### US-311 · Hỏi tiếp theo ngữ cảnh · **P2** · 5 điểm
> Là **chuyên viên BD**, tôi muốn hỏi tiếp một câu ngắn dựa trên câu trả lời trước (ví dụ "còn hợp đồng năm 2024 thì sao?"), để không phải nhắc lại toàn bộ ngữ cảnh.

- **AC-311.1** — *Given* 10 cặp câu hỏi nối tiếp kiểm thử, *When* chạy, *Then* ≥ 8 câu hỏi nối tiếp được trả lời đúng ngữ cảnh câu trước.
- **AC-311.2** — *Given* một câu hỏi nối tiếp, *When* truy xuất, *Then* hệ thống dùng tối đa 2 lượt hỏi đáp gần nhất làm ngữ cảnh.

| Truy vết | BR-010, SN-001 · UCD-17 · `[PRD-new]` |
|---|---|
| Phụ thuộc | US-302, US-308 |

---

## E4. Đo lường giá trị

### US-401 · Trang số liệu hằng tuần · **P1** · 5 điểm
> Là **quản lý**, tôi muốn xem trang số liệu hằng tuần (người dùng hoạt động, số câu hỏi, tỉ lệ "không tìm thấy", tỉ lệ hữu ích, thời gian trả lời p95), để đánh giá MVP sau 4 tuần.

- **AC-401.1** — *Given* tôi là Trưởng nhóm BD hoặc Quản lý, *When* mở trang số liệu và chọn 4 / 8 / 12 tuần, *Then* tôi thấy 5 chỉ số theo từng tuần, so với mục tiêu OKR.
- **AC-401.2** — *Given* tôi là Thành viên BD, *When* truy cập trang số liệu, *Then* mục menu không hiện và API trả `403`.
- **AC-401.3** — *Given* dữ liệu sự kiện, *When* tính chỉ số, *Then* không dùng nội dung câu hỏi; người dùng chỉ được đếm qua mã băm.

| Truy vết | SN-002 · UCD-26 · M-003 · KR1.2, KR3.1, KR3.2 |
|---|---|
| Phụ thuộc | EN-08 |

### US-402 · Chạy bộ câu hỏi kiểm thử và xuất kết quả · **P2** · 5 điểm
> Là **trưởng nhóm BD**, tôi muốn chạy bộ câu hỏi kiểm thử và xuất kết quả ra bảng tính để chấm, để có số liệu M-002 khi nghiệm thu.

- **AC-402.1** — *Given* một file .xlsx đúng mẫu (≤ 200 dòng), *When* tôi chạy, *Then* tôi thấy tiến độ và nhận file kết quả gồm câu hỏi, câu trả lời, trích dẫn, cột để chấm.
- **AC-402.2** — *Given* file sai mẫu, *When* tôi tải lên, *Then* hệ thống nêu đúng dòng và cột bị lỗi.
- **AC-402.3** — *Given* lần chạy quá 60 phút, *When* hết giờ, *Then* hệ thống dừng và giữ kết quả đã có.

| Truy vết | UC-05 · UCD-27, UCD-28 · DEP-003 · M-002 |
|---|---|
| Phụ thuộc | EN-10 (harness đánh giá) |

---

## EN. Enabler kỹ thuật (từ SAD và Blueprint)

| ID | Tên | Điểm | Mô tả | Tiêu chí hoàn thành | Truy vết |
|---|---|---|---|---|---|
| EN-01 | Khởi tạo repo và CI | 3 | Cấu trúc repo theo Blueprint §3.1; lint, format, import-linter (DR-1 → DR-5), test chạy trong CI | Pull request đầu tiên chạy CI xanh; vi phạm quy tắc import làm CI đỏ | SAD ADR-01, Blueprint §3.3, QAS-09 |
| EN-02 | Hạ tầng và môi trường | 8 | Môi trường dev / staging; PostgreSQL 16 + pgvector; object storage có mã hoá; secrets manager; OIDC client; TLS | `docker compose up` chạy được ở máy dev; staging truy cập được qua HTTPS; secrets không nằm trong repo | ADR-04, ADR-06, ADR-10, ADR-12, SEC-02, SEC-03 |
| EN-03 | Dịch vụ embedder + benchmark | 5 | Container BGE-M3 (CPU); đo tốc độ lập chỉ mục và độ trễ truy vấn | Báo cáo benchmark: file 300 trang ≤ 5 phút; truy vấn ≤ 200 ms p95. Nếu không đạt thì có đề xuất (thêm bản sao / GPU) | ADR-08, **TQ-02**, NFR-03 |
| EN-04 | Pipeline xử lý tài liệu | 8 | Worker + hàng đợi trong PostgreSQL; trích xuất theo trang; phát hiện mật khẩu / hỏng / không có chữ; chia đoạn (ALG-1); thử lại 3 lần | File 50 MB / 300 trang đạt "Sẵn sàng" ≤ 5 phút; chạy lại không tạo đoạn trùng (idempotent) | ADR-05, ALG-1, SAD §2.2 |
| EN-05 | Truy xuất lai (ChunkIndex) | 8 | Vector HNSW + FTS + RRF, top 8, ≤ 3 đoạn / tài liệu; ngưỡng `τ` trong cấu hình | ≤ 250 ms p95 với 300.000 đoạn; chỉ trả đoạn của tài liệu READY chưa gỡ | ADR-07, ALG-2 |
| EN-06 | AnswerGenerator adapter | 5 | Adapter LLM có streaming; timeout (3 s / 10 s / 28 s); thử lại 1 lần; circuit breaker; semaphore 10 lời gọi | Test với fake LLM: timeout, lỗi 429 / 503, mở và đóng circuit breaker đều đúng kịch bản | ADR-09, ALG-4, REL-04, NFR-08 |
| EN-07 | Observability | 5 | OpenTelemetry (trace 8 span), metrics Prometheus, log JSON có lọc nội dung, 9 cảnh báo | Một câu hỏi tạo trace đầu-cuối; test tự động xác nhận log không có trường nội dung | SAD §4.3, QAS-06, QAS-11, LG-15, LG-17 |
| EN-08 | Sự kiện phân tích | 3 | Bảng `analytics.event` phân vùng theo tháng; danh sách thuộc tính cho phép; `user_id_hash` bằng HMAC; `POST /events` | 13 sự kiện của PRD §5.2 được ghi; sự kiện có thuộc tính lạ bị từ chối | PRD §5.2, LG-15 |
| EN-09 | Bảo mật nền tảng | 5 | CSP, CSRF, giới hạn tần suất, audit log chỉ ghi thêm, job purge ≤ 24 h, quét lỗ hổng trong CI | 0 lỗ hổng Critical / High; purge xoá cả object và đoạn văn bản | SAD §4.1, SEC-05, SEC-06, LG-11 |
| EN-10 | Bộ câu hỏi kiểm thử và harness đánh giá | 3 | Nhận bộ tài liệu mẫu + câu hỏi có đáp án (DEP-003); script chạy đánh giá trong CI ban đêm | Báo cáo tự động: KR2.1, KR2.2, KR2.3 sau mỗi lần đổi prompt / `τ` / top-k | DEP-003, LG-03 → LG-05, TQ-07 |
| EN-11 | Design system thành code | 5 | Chuyển token (`tokens.css`) và component của [design-system.html](../04-design/UI_UX_design/design-system.html) sang React | Component dùng lại được ở mọi màn hình; lint CSS chặn mã màu viết trực tiếp | Blueprint §3.6, UX-S05 |
| EN-12 | Bộ test E2E và test hiệu năng | 5 | E2E cho F1 → F6; test 100 câu hỏi đo p95; kiểm tra truy cập trái phép; axe | Bộ test chạy trên staging; báo cáo p95 và tỉ lệ lỗi | LG-01, LG-06, LG-08, LG-10, LG-13, LG-14 |

---

## Ma trận truy vết: yêu cầu → story

| Yêu cầu BRD | Ưu tiên | Story |
|---|---|---|
| BR-001 | Must | US-201, US-202, EN-04 |
| BR-002 | Must | US-301 |
| BR-003 | Must | US-302, EN-05, EN-06 |
| BR-004 | Should | US-203 |
| BR-005 | Should | US-204 |
| BR-006 | Should | US-205 |
| BR-007 | Must | US-303, US-305 |
| BR-008 | Must | US-304 |
| BR-009 | Should (PQ-006) | US-306, US-310 |
| BR-010 | Could | US-308, US-311 |
| BR-011, BR-013 | Won't | — (ngoài MVP) |
| BR-012 | Must | US-101, US-102 |
| BR-014 | Should | EN-07 (giám sát, cảnh báo), EN-02 (2 bản sao) |
| PD-03, KR3.2 | `[PRD-new]` | US-309 |
| SN-002 | — | US-401 |
| UC-05, DEP-003 | — | US-402, EN-10 |
