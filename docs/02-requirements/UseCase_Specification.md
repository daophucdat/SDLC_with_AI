# Use Case Specification — Chat với tài liệu (MVP)

| Thuộc tính | Giá trị |
|---|---|
| Tài liệu | UCS-001 |
| Phiên bản | 0.1 |
| Ngày cập nhật | 2026-10-19 |
| Trạng thái | **Draft** (chờ review) |
| Tác giả | AI Requirements Agent |
| Người review / phê duyệt | BA (review); Trưởng nhóm BD (nghiệm thu nghiệp vụ); người phê duyệt `[TBD: OQ-003]` |
| Đầu vào | [BRD v0.3](BRD.md), [PRD v0.2](PRD.md), [Use case diagram](UseCase_ChatVoiTaiLieu.drawio) |

Tài liệu này mô tả **điều gì xảy ra** giữa người dùng và hệ thống, không mô tả giao diện trông như thế nào. Giao diện: [UI/UX design](../04-design/UI_UX_design/index.html). Mã use case `UCD-xx` khớp với use case diagram.

---

## 0. Danh mục use case

| ID | Tên | Đặc tả ở | Quan hệ |
|---|---|---|---|
| UCD-01 | Đăng nhập | §1 | «include» UCD-02 |
| UCD-02 | Xác thực và kiểm tra quyền truy cập | §1 (bước 3–5) | được include bởi UCD-01 |
| UCD-03 | Kết thúc phiên làm việc | §1 (A2, A3) | — |
| UCD-04 | Tải tài liệu PDF lên | §2 | «include» UCD-05, UCD-06 |
| UCD-05 | Kiểm tra định dạng và dung lượng file | §2 (bước 2) | được include |
| UCD-06 | Xử lý và trích xuất nội dung tài liệu | §2 (bước 6–8) | được include |
| UCD-07 | Cảnh báo file không đọc được chữ | §2 (E4) | «extend» UCD-06 |
| UCD-08 | Cảnh báo file trùng | §2 (A1) | «extend» UCD-04 |
| UCD-09 | Theo dõi trạng thái xử lý | §2 (bước 5–8) | — |
| UCD-10 | Xem danh sách tài liệu | §3 (bước 1) | — |
| UCD-14 | Lọc tài liệu theo tên | §3 (A3) | «extend» UCD-10 |
| UCD-11 | Gỡ tài liệu | §3 | «include» UCD-15; là cha của UCD-12, UCD-13 |
| UCD-12 / UCD-13 | Gỡ tài liệu do mình tải lên / Gỡ mọi tài liệu | §3 | generalization của UCD-11 |
| UCD-15 | Xác nhận gỡ tài liệu | §3 (bước 3–4) | được include |
| UCD-16 | Đặt câu hỏi | §4 | «include» UCD-19 |
| UCD-17 | Hỏi tiếp theo ngữ cảnh | §4 (A1) | generalization của UCD-16 |
| UCD-18 | Xem lại lịch sử hội thoại | §4 (A6) | — |
| UCD-19, UCD-20 | Tổng hợp câu trả lời; Gắn trích dẫn | §4 (bước 4–8) | được include |
| UCD-21 | Thông báo "không tìm thấy" | §4 (E1, E2) | «extend» UCD-19 |
| UCD-22 → UCD-25 | Mở trang nguồn; Dừng; Sao chép kèm nguồn; Đánh giá | §4 (A2 → A5) | «extend» UCD-16 |
| UCD-26 | Xem trang số liệu sử dụng | §5 | — |
| UCD-27, UCD-28 | Chạy bộ câu hỏi kiểm thử; Xuất kết quả | §6 | «include» UCD-28 |

---

## 1. UCD-01 — Đăng nhập

| Mục | Nội dung |
|---|---|
| **Mô tả** | Thành viên đội BD vào hệ thống bằng tài khoản công ty; người không thuộc đội BD bị từ chối. |
| **Primary actor** | Người dùng được cấp quyền (Thành viên BD, Trưởng nhóm BD, Quản lý) |
| **Secondary actor** | Hệ thống tài khoản công ty (IF-01) |
| **Phạm vi** | Hệ thống chịu trách nhiệm phiên làm việc và phân quyền. Việc cấp và thu hồi nhóm người dùng do IT thực hiện trên hệ thống tài khoản, nằm ngoài phạm vi (DEP-002) |
| **Trigger** | Người dùng mở đường dẫn của hệ thống khi chưa có phiên hợp lệ |
| **Pre-conditions** | Người dùng có tài khoản công ty đang hoạt động |
| **Post-conditions (thành công)** | Có phiên làm việc mới gắn với vai trò của người dùng; người dùng ở màn hình làm việc; ghi nhật ký kiểm toán "đăng nhập" |
| **Post-conditions (thất bại)** | Không tạo phiên; không lộ bất kỳ thông tin tài liệu nào; ghi nhật ký "từ chối truy cập" nếu người dùng không có quyền |

**Main success scenario**

1. Người dùng yêu cầu đăng nhập.
2. Hệ thống chuyển người dùng tới hệ thống tài khoản công ty.
3. Người dùng xác thực tại hệ thống tài khoản công ty.
4. Hệ thống tài khoản công ty trả về danh tính và nhóm của người dùng.
5. Hệ thống xác định vai trò từ nhóm (BD_MEMBER, BD_LEAD, MANAGER) **(UCD-02)**.
6. Hệ thống tạo phiên làm việc và đưa người dùng vào màn hình làm việc trong ≤ 5 giây.

**Alternate flows**

- **A1 (từ bước 1):** người dùng đã có phiên còn hiệu lực → hệ thống bỏ qua bước 2–6 và vào thẳng màn hình làm việc.
- **A2 — Kết thúc phiên (UCD-03):** người dùng chọn đăng xuất → hệ thống xoá phiên **và toàn bộ hội thoại của phiên** (PD-04).
- **A3 — Hết phiên (UCD-03):** sau 8 giờ không hoạt động, ở thao tác tiếp theo hệ thống yêu cầu đăng nhập lại; câu hỏi đang soạn dở được giữ lại (EC-17).

**Exception flows**

- **E1 (từ bước 5):** người dùng không thuộc nhóm nào được cấp quyền → hệ thống từ chối, đề nghị liên hệ Trưởng nhóm BD (EC-18).
- **E2 (từ bước 3):** hệ thống tài khoản công ty không phản hồi → hệ thống báo "chưa đăng nhập được" và cho phép thử lại.

| Mục | Nội dung |
|---|---|
| **Business rules** | RUL-001: chỉ thành viên đội BD được cấp quyền mới truy cập. Ánh xạ nhóm → vai trò theo PRD 6.3 |
| **Non-functional** | SEC-01 (100% truy cập trái phép bị từ chối); SEC-02 (mã hoá đường truyền); SEC-05 (nhật ký kiểm toán); phiên hết hạn sau 8 giờ không hoạt động |
| **Dữ liệu** | Vào: danh tính (email), nhóm. Lưu: người dùng (email, tên hiển thị, vai trò), phiên (thời điểm tạo, thời điểm hoạt động gần nhất) |
| **Truy vết** | US-101, US-102, US-103; BR-012; AC-012; LG-10 |

---

## 2. UCD-04 — Tải tài liệu PDF lên

| Mục | Nội dung |
|---|---|
| **Mô tả** | Người dùng đưa một hoặc nhiều file PDF vào kho chung để dùng làm nguồn cho câu trả lời. |
| **Primary actor** | Người dùng được cấp quyền |
| **Secondary actor** | — (lưu trữ file và xử lý nội dung nằm trong hệ thống) |
| **Phạm vi** | Kho tài liệu chung của đội BD (PD-01) |
| **Trigger** | Người dùng chọn hoặc kéo-thả file để tải lên |
| **Pre-conditions** | Đã đăng nhập (UCD-01); có kết nối mạng |
| **Post-conditions (thành công)** | Tài liệu ở trạng thái **Sẵn sàng** và được dùng cho câu hỏi tiếp theo; ghi nhật ký "tải lên" |
| **Post-conditions (thất bại)** | Kho không thay đổi (file bị từ chối hoặc tải lên thất bại), **hoặc** tài liệu ở trạng thái *Không đọc được chữ* / *Lỗi* và không được dùng để trả lời |

**Main success scenario** (cho mỗi file)

1. Người dùng chọn file.
2. Hệ thống kiểm tra file là PDF và ≤ 50 MB **(UCD-05)**.
3. Hệ thống nhận file và hiển thị tiến độ.
4. Hệ thống lưu file vào kho.
5. Hệ thống báo tài liệu ở trạng thái *Đang xử lý* **(UCD-09)**.
6. Hệ thống trích xuất văn bản theo từng trang **(UCD-06)**.
7. Hệ thống lập chỉ mục nội dung theo trang.
8. Hệ thống đặt trạng thái *Sẵn sàng* và báo người dùng "đã sẵn sàng để hỏi" (≤ 5 phút cho file 50 MB / 300 trang).

**Alternate flows**

- **A1 — File trùng (UCD-08, từ bước 2):** nội dung trùng với một tài liệu đang có → hệ thống hỏi người dùng có tải thêm bản trùng không. Đồng ý → tiếp bước 3. Không → kết thúc, kho không đổi.
- **A2 — Nhiều file (từ bước 1):** mỗi file đi qua bước 2–8 độc lập; file lỗi không chặn file khác.

**Exception flows**

- **E1 (từ bước 2):** không phải PDF hoặc > 50 MB → hệ thống từ chối và nêu đúng lý do (EC-07, EC-08).
- **E2 (từ bước 3):** mất kết nối → hệ thống tạm dừng và tự thử lại tối đa 3 lần; vẫn lỗi → báo lỗi, cho phép thử lại (EC-04). Người dùng có thể huỷ trong lúc tải.
- **E3 (từ bước 6):** file có mật khẩu hoặc hỏng → trạng thái *Lỗi* kèm lý do; cho phép thử lại hoặc gỡ (EC-09, EC-11).
- **E4 — Không đọc được chữ (UCD-07, từ bước 6):** file dạng ảnh scan → trạng thái *Không đọc được chữ*; tài liệu không được dùng để trả lời (BR-006, EC-10).

| Mục | Nội dung |
|---|---|
| **Business rules** | Chỉ PDF dạng văn bản (CON-002); ≤ 50 MB / file (BR-001); kho dùng chung cho cả đội (PD-01); tài liệu chỉ được dùng để trả lời khi ở trạng thái Sẵn sàng |
| **Non-functional** | NFR-03 (≤ 5 phút); SEC-03 (mã hoá khi lưu); REL-05 (tự thử lại) |
| **Dữ liệu** | Vào: file (tên, dung lượng, nội dung). Lưu: tài liệu (tên file, dung lượng, số trang, mã băm nội dung, trạng thái, lý do lỗi, người tải lên, thời điểm); nội dung theo trang |
| **Truy vết** | US-201, US-202, US-205, US-206; BR-001, BR-006; AC-001, AC-006; LG-07 |

---

## 3. UCD-11 — Gỡ tài liệu

| Mục | Nội dung |
|---|---|
| **Mô tả** | Người có quyền gỡ một tài liệu khỏi kho để nó không còn được dùng cho câu trả lời mới. Hai biến thể: **UCD-12** gỡ tài liệu do mình tải lên (mọi vai trò); **UCD-13** gỡ mọi tài liệu (chỉ Trưởng nhóm BD). |
| **Primary actor** | Người dùng được cấp quyền (UCD-12); Trưởng nhóm BD (UCD-13) |
| **Trigger** | Người dùng chọn gỡ một tài liệu |
| **Pre-conditions** | Đã đăng nhập; tài liệu tồn tại trong kho; người dùng có quyền gỡ tài liệu đó (PD-02) |
| **Post-conditions (thành công)** | Tài liệu biến khỏi kho; không câu trả lời mới nào trích từ nó; file và nội dung bị xoá vĩnh viễn trong ≤ 24 giờ; ghi nhật ký "gỡ" |
| **Post-conditions (thất bại)** | Tài liệu giữ nguyên |

**Main success scenario**

1. Người dùng xem danh sách tài liệu **(UCD-10)**.
2. Người dùng chọn gỡ một tài liệu.
3. Hệ thống yêu cầu xác nhận, nêu rõ việc gỡ ảnh hưởng tới cả đội và không hoàn tác được **(UCD-15)**.
4. Người dùng xác nhận.
5. Hệ thống gỡ tài liệu khỏi kho và báo thành công.
6. Hệ thống xoá vĩnh viễn file và nội dung trong ≤ 24 giờ.

**Alternate flows**

- **A1 (từ bước 4):** người dùng huỷ → kết thúc, tài liệu giữ nguyên.
- **A2 (sau bước 5):** các câu trả lời cũ trong hội thoại hiện tại vẫn hiển thị trích dẫn tới tài liệu này, nhưng đánh dấu "đã gỡ" và không mở được (EC-15, EC-16).
- **A3 — Lọc (UCD-14, ở bước 1):** người dùng lọc danh sách theo tên (≥ 2 ký tự).

**Exception flows**

- **E1 (từ bước 2):** người dùng không có quyền → hệ thống không cho phép thao tác gỡ; nếu yêu cầu vẫn đến được hệ thống thì bị từ chối.

| Mục | Nội dung |
|---|---|
| **Business rules** | PD-02: chỉ người tải lên và Trưởng nhóm BD được gỡ; RUL-003: tài liệu đã gỡ không được dùng cho câu trả lời mới |
| **Non-functional** | SEC-06 (xoá vĩnh viễn ≤ 24 giờ); SEC-05 (nhật ký kiểm toán) |
| **Dữ liệu** | Vào: mã tài liệu. Lưu: thời điểm gỡ, người gỡ |
| **Truy vết** | US-203, US-204; BR-004, BR-005; AC-004, AC-005 |

---

## 4. UCD-16 — Đặt câu hỏi

| Mục | Nội dung |
|---|---|
| **Mô tả** | Người dùng hỏi bằng tiếng Việt hoặc tiếng Anh và nhận câu trả lời tổng hợp từ các tài liệu liên quan, mỗi ý có trích dẫn tài liệu và trang; nếu tài liệu không có thông tin thì được báo "không tìm thấy". |
| **Primary actor** | Người dùng được cấp quyền |
| **Secondary actor** | Dịch vụ AI (IF-02) |
| **Phạm vi** | Hệ thống tìm đoạn liên quan, kiểm tra trích dẫn và trình bày kết quả. Dịch vụ AI chỉ soạn câu trả lời từ các đoạn được cung cấp |
| **Trigger** | Người dùng gửi một câu hỏi |
| **Pre-conditions** | Đã đăng nhập; kho có ≥ 1 tài liệu Sẵn sàng (EC-01, EC-03) |
| **Post-conditions (thành công)** | Câu trả lời *Hoàn tất* có ≥ 1 trích dẫn hợp lệ, được lưu trong hội thoại của phiên; ghi sự kiện chỉ có siêu dữ liệu |
| **Post-conditions (thất bại)** | Câu trả lời ở trạng thái *Không tìm thấy*, *Đã dừng* hoặc *Lỗi*, kèm hướng dẫn bước tiếp theo; không có câu trả lời nào được hiển thị mà thiếu trích dẫn hợp lệ |

**Main success scenario**

1. Người dùng nhập câu hỏi (1–2.000 ký tự).
2. Hệ thống kiểm tra câu hỏi và ghi nhận câu hỏi.
3. Hệ thống báo đang tìm trong N tài liệu.
4. Hệ thống tìm các đoạn liên quan nhất trong các tài liệu Sẵn sàng **(UCD-19)**.
5. Hệ thống gửi câu hỏi và các đoạn liên quan cho Dịch vụ AI.
6. Dịch vụ AI soạn câu trả lời kèm số thứ tự đoạn được dùng.
7. Hệ thống hiển thị dần câu trả lời trong lúc nhận (phần đầu ≤ 5 giây).
8. Hệ thống kiểm tra mọi trích dẫn và gắn tài liệu + trang cho từng trích dẫn **(UCD-20)**.
9. Hệ thống hiển thị câu trả lời hoàn tất kèm danh sách nguồn (≤ 30 giây ở p95).

**Alternate flows**

- **A1 — Hỏi tiếp (UCD-17, từ bước 1):** câu hỏi nối tiếp ngắn được hiểu theo ngữ cảnh 2 lượt hỏi đáp gần nhất.
- **A2 — Mở trang nguồn (UCD-22, sau bước 9):** người dùng chọn một trích dẫn → hệ thống mở đúng tài liệu, đúng trang và đánh dấu đoạn liên quan (≤ 2 giây).
- **A3 — Dừng (UCD-23, ở bước 7):** người dùng yêu cầu dừng → hệ thống ngừng, giữ phần đã có và đánh dấu "Đã dừng".
- **A4 — Sao chép (UCD-24, sau bước 9):** người dùng sao chép câu trả lời kèm danh sách nguồn.
- **A5 — Đánh giá (UCD-25, sau bước 9):** người dùng đánh giá hữu ích / chưa tốt; nếu chưa tốt thì chọn lý do.
- **A6 — Xem lại (UCD-18):** người dùng xem lại các lượt hỏi đáp của phiên hiện tại.

**Exception flows**

- **E1 — Không có đoạn liên quan (UCD-21, từ bước 4):** hệ thống báo "không tìm thấy trong N tài liệu" kèm gợi ý diễn đạt lại; không gọi Dịch vụ AI.
- **E2 — Trích dẫn không hợp lệ (UCD-21, từ bước 8):** hệ thống thay nội dung đã hiển thị bằng thông báo "không tìm thấy" (EC-14, TQ-01).
- **E3 — Quá 30 giây hoặc Dịch vụ AI lỗi (từ bước 5–7):** hệ thống báo "chưa trả lời được", cho phép thử lại; nếu Dịch vụ AI lỗi liên tục thì tạm ngưng hỏi đáp nhưng kho tài liệu vẫn dùng được (EC-13, REL-04).
- **E4 — Mất kết nối (từ bước 7):** hệ thống giữ phần đã nhận, đánh dấu "chưa hoàn chỉnh", cho phép hỏi lại (EC-05).
- **E5 (từ bước 2):** câu hỏi rỗng hoặc > 2.000 ký tự → không gửi được.

| Mục | Nội dung |
|---|---|
| **Business rules** | RUL-002: câu trả lời chỉ dựa trên tài liệu trong kho; mỗi ý phải có trích dẫn; tài liệu chưa Sẵn sàng hoặc đã gỡ không được dùng |
| **Non-functional** | NFR-01 (≤ 30 giây p95), NFR-02 (≤ 5 giây), NFR-05 (mở nguồn ≤ 2 giây); SEC-04 (chỉ gửi ≤ 8 đoạn cho Dịch vụ AI, không dùng để huấn luyện); không ghi nội dung câu hỏi vào dữ liệu phân tích (PRD 5.2) |
| **Dữ liệu** | Vào: nội dung câu hỏi, mã hội thoại. Ra: nội dung trả lời, trạng thái, danh sách trích dẫn (số thứ tự, tài liệu, trang, đoạn trích ≤ 200 ký tự), thời gian trả lời. Phản hồi: giá trị, lý do |
| **Truy vết** | US-301 → US-311; BR-002, 003, 007 → 010; AC-002, 003, 007, 008, 009; LG-03 → LG-06; [sequence diagram](SequenceDiagram_ChatVoiTaiLieu.drawio) |

---

## 5. UCD-26 — Xem trang số liệu sử dụng

| Mục | Nội dung |
|---|---|
| **Mô tả** | Trưởng nhóm BD hoặc Quản lý xem chỉ số sử dụng và chất lượng theo tuần để đánh giá MVP. |
| **Primary actor** | Trưởng nhóm BD, Quản lý |
| **Secondary actor** | Công cụ phân tích sản phẩm (IF-04) |
| **Trigger** | Người dùng mở trang số liệu |
| **Pre-conditions** | Đã đăng nhập với vai trò BD_LEAD hoặc MANAGER |
| **Post-conditions (thành công)** | Người dùng thấy các chỉ số tuần: tỉ lệ người dùng hoạt động, số câu hỏi, tỉ lệ "không tìm thấy", tỉ lệ hữu ích, thời gian trả lời p95 |
| **Post-conditions (thất bại)** | Không hiển thị số liệu; không lộ nội dung câu hỏi |

**Main success scenario**

1. Người dùng chọn xem số liệu.
2. Hệ thống kiểm tra vai trò.
3. Người dùng chọn khoảng thời gian (4 / 8 / 12 tuần).
4. Hệ thống tổng hợp chỉ số theo tuần và so với mục tiêu OKR.

**Alternate flows**

- **A1 (từ bước 4):** chưa có dữ liệu cho khoảng đã chọn → hệ thống báo chưa có dữ liệu.

**Exception flows**

- **E1 (từ bước 2):** vai trò Thành viên BD → không được truy cập.

| Mục | Nội dung |
|---|---|
| **Business rules** | Chỉ BD_LEAD và MANAGER xem được (PRD 6.3) |
| **Non-functional** | Dữ liệu chỉ là siêu dữ liệu, mã người dùng được băm (PRD 5.2) |
| **Dữ liệu** | Ra: tuần, tỉ lệ người dùng hoạt động, số câu hỏi, tỉ lệ không tìm thấy, tỉ lệ hữu ích, p95 |
| **Truy vết** | US-401; SN-002; M-003; KR1.2, KR3.1, KR3.2 |

---

## 6. UCD-27 — Chạy bộ câu hỏi kiểm thử

| Mục | Nội dung |
|---|---|
| **Mô tả** | Trưởng nhóm BD chạy bộ câu hỏi có đáp án qua đúng quy trình hỏi đáp, rồi xuất kết quả để chấm chất lượng (M-002). |
| **Primary actor** | Trưởng nhóm BD |
| **Trigger** | Trưởng nhóm BD gửi một bộ câu hỏi kiểm thử |
| **Pre-conditions** | Đã đăng nhập với vai trò BD_LEAD; kho có các tài liệu mẫu của bộ kiểm thử (DEP-003) |
| **Post-conditions (thành công)** | Có file kết quả gồm câu hỏi, câu trả lời, trích dẫn và cột để chấm **(UCD-28)** |
| **Post-conditions (thất bại)** | Không có kết quả; hệ thống chỉ rõ dòng và cột bị lỗi trong bộ câu hỏi |

**Main success scenario**

1. Trưởng nhóm BD gửi bộ câu hỏi (≤ 200 dòng).
2. Hệ thống kiểm tra đúng mẫu (các cột câu hỏi, đáp án mong đợi, có phải câu "không có đáp án" không).
3. Hệ thống chạy từng câu qua quy trình hỏi đáp (§4) và báo tiến độ.
4. Hệ thống xuất file kết quả (UCD-28).
5. Trưởng nhóm BD chấm và so với ngưỡng ra mắt LG-03 → LG-05.

**Exception flows**

- **E1 (từ bước 2):** sai mẫu → hệ thống báo lỗi theo dòng và cột.
- **E2 (từ bước 3):** quá 60 phút → hệ thống dừng lần chạy, giữ kết quả đã có.

| Mục | Nội dung |
|---|---|
| **Business rules** | Chỉ BD_LEAD được chạy; kết quả giữ 12 tháng |
| **Non-functional** | ≤ 60 phút mỗi lần chạy (CN-16) |
| **Dữ liệu** | Vào: câu hỏi, đáp án mong đợi, cờ "không có đáp án". Ra: câu trả lời, trích dẫn, trạng thái, cột điểm |
| **Truy vết** | US-402; UC-05; DEP-003; M-002 |

---

## 7. Giả định

| ID | Giả định | Ảnh hưởng | Kiểm chứng |
|---|---|---|---|
| ASM-001 → ASM-005 | Kế thừa từ BRD §10 (vấn đề chính, bối cảnh, loại file, quy mô, ngôn ngữ) | Toàn bộ | Theo BRD |
| UA-01 | Mọi thành viên BD dùng chung một kho (PD-01) | §2, §3 | PQ-001 |
| UA-02 | Hệ thống tài khoản công ty cung cấp được thông tin nhóm để xác định vai trò | §1 | DEP-002, OQ-005 |
| UA-03 | Lịch sử hội thoại không cần giữ sau khi đăng xuất | §1 A2, §4 A6 | PQ-003 |

## 8. Vấn đề còn mở (parking lot)

| ID | Câu hỏi | Use case | Người quyết định |
|---|---|---|---|
| PQ-001 | Kho chung hay kho riêng cho từng người? | UCD-04, UCD-11 | Quản lý |
| PQ-002 | Ai được gỡ tài liệu? | UCD-11 → 13 | Trưởng nhóm BD |
| TQ-01 | Có giữ cách "hiện dần rồi thay bằng không tìm thấy" (E2 của §4) không? | UCD-16 | Quản lý + BA |
| OQ-008 | Tài liệu có được gửi cho Dịch vụ AI bên ngoài không? | UCD-16 | IT / Bảo mật |
| OQ-014 | Ngôn ngữ câu hỏi và tài liệu | UCD-16 | BA |
| OQ-021 | Tài liệu có dữ liệu cá nhân không; cần lưu vết ai đã hỏi gì không? | UCD-01, UCD-16 | IT / Bảo mật |
