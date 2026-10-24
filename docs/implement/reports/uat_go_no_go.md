# UAT, Go / No-go và ra mắt thử nghiệm (REL-03)

## 1. UAT trên staging

**Người tham gia:** 5 thành viên BD (gồm Trưởng nhóm), tài liệu thật đã được IT cho phép. **Thời lượng:** 2 buổi × 60 phút.

| Luồng | Việc người dùng làm | Đạt khi | Kết quả (5 người) | Lỗi / phản hồi |
|---|---|---|---|---|
| F1 Đăng nhập | Mở đường dẫn, đăng nhập bằng tài khoản công ty | Vào màn hình làm việc, thấy tên mình | | |
| F2 Tải tài liệu | Kéo-thả 3 file PDF của mình (1 file scan nếu có) | Thấy tiến độ, trạng thái, lý do khi lỗi | | |
| F3 Hỏi đáp | Hỏi 5 câu thật trong công việc | Câu trả lời có nguồn; câu không có đáp án báo "không tìm thấy" | | |
| F4 Kiểm chứng | Bấm `[1]`, xem trang nguồn; sao chép kèm nguồn | Mở đúng trang ≤ 2 s; đoạn được tô sáng | | |
| F5 Gỡ / lọc | Lọc theo tên; gỡ 1 file mình đã tải | Chỉ thấy "Gỡ" với file của mình | | |
| F6 Số liệu (Trưởng nhóm) | Xem trang Số liệu; chạy bộ câu hỏi kiểm thử | Thấy chỉ số theo tuần; tải được file kết quả | | |

**UX-S01:** ≥ 4/5 người tự tải file và nhận câu trả lời có nguồn đầu tiên trong ≤ 3 phút, không cần hướng dẫn. Kết quả: ___/5.

## 2. Hướng dẫn sử dụng (1 trang — in / gửi kèm thư mời)

> **Chat với tài liệu — hỏi đáp trên tài liệu PDF của đội BD**
>
> 1. **Đăng nhập** bằng tài khoản công ty tại `https://chat-tai-lieu.congty.vn`.
> 2. **Tải tài liệu**: kéo-thả file PDF vào cột "Kho tài liệu" (tối đa 50 MB/file). Chờ trạng thái **Sẵn sàng**. Kho dùng chung cho cả đội.
> 3. **Hỏi** bằng tiếng Việt hoặc tiếng Anh trong ô dưới cùng, nhấn **Enter** (Shift+Enter để xuống dòng).
> 4. **Kiểm chứng**: mỗi ý có số `[1]`, `[2]`… — bấm vào để mở đúng trang trong file gốc, đoạn liên quan được tô vàng.
> 5. **"Không tìm thấy"** nghĩa là thông tin không có trong các tài liệu hiện có — hãy diễn đạt lại hoặc tải thêm tài liệu. Hệ thống không bịa câu trả lời.
> 6. **Sao chép kèm nguồn** để dán vào email / báo cáo; bấm 👍 / 👎 để giúp đội cải thiện.
> 7. File **dạng ảnh scan** không đọc được chữ và không được dùng để trả lời. Chỉ người tải lên (hoặc Trưởng nhóm) gỡ được tài liệu.
> 8. Phiên tự kết thúc sau 8 giờ không dùng; câu đang gõ dở được giữ lại.
>
> Hỗ trợ: kênh chat `#chat-tai-lieu-ho-tro` · Đầu mối phản hồi: Trưởng nhóm BD.

Buổi giới thiệu 30 phút: 10 phút demo F1 → F4 · 10 phút mọi người tự làm với tài liệu của mình · 10 phút hỏi đáp.

## 3. Biên bản họp Go / No-go

| Mục | Nội dung |
|---|---|
| Ngày họp | |
| Thành phần | Quản lý (quyết định), IT / Bảo mật, Trưởng nhóm BD, Tech lead, QA |
| Đầu vào | `launch_gates.md` (17 LG), `restore_runbook.md` (biên bản diễn tập REL-02), kết quả UAT ở mục 1 |
| LG chưa đạt | (liệt kê; mỗi LG kèm kế hoạch + ngày, hoặc ghi là lý do No-go) |
| Rủi ro chấp nhận | (ví dụ TQ-05, DQ-03 — phiên còn hiệu lực sau khi rút quyền tới khi hết hạn) |
| **Quyết định** | ☐ Go ☐ Go có điều kiện ☐ No-go |
| Xác nhận (OQ-003) | Quản lý: ______ · IT / Bảo mật: ______ · Trưởng nhóm BD: ______ |

## 4. Ra mắt theo đợt (nếu Go)

| Đợt | Thời gian | Ai | Cách cấp quyền | Theo dõi |
|---|---|---|---|---|
| 1 | Tuần 1 | 5 người (UAT) | Thêm vào nhóm `grp-bd-member` / `grp-bd-lead` trên IdP | Dashboard vận hành hằng ngày; kênh hỗ trợ |
| 2 | Tuần 2 | Toàn đội (30 tài khoản) | Thêm cả nhóm BD | Trang Số liệu hằng tuần |

## 5. Phương án tắt nhanh (đã thử trên staging: ☐)

| Tình huống | Hành động | Thời gian | Ảnh hưởng |
|---|---|---|---|
| Câu trả lời sai / rủi ro nội dung | `FEATURE_FLAGS=…,qa_off` + khởi động lại `api` | < 5 phút | Hỏi đáp tắt, banner "Hỏi đáp tạm gián đoạn"; kho tài liệu và trang nguồn vẫn dùng được |
| Cần dừng toàn bộ | Gỡ nhóm khỏi ứng dụng trên IdP | < 15 phút | Lần đăng nhập mới bị từ chối; phiên đang mở hết hạn sau tối đa 8 giờ (DQ-03) — nếu cần ngay: `DELETE FROM access.session;` |
| Chi phí AI tăng đột biến | Giảm `LLM_MAX_OUTPUT_TOKENS` / `RETR_TOPN`, hoặc `qa_off` | < 5 phút | Câu trả lời ngắn hơn |

## 6. Sau ra mắt

- Hằng tuần: trang Số liệu (WAU, p95, "hữu ích", "không tìm thấy", số câu hỏi) + số câu trả lời bị ALG-3 thay bằng "không tìm thấy" (`qa_citation_invalid_total`, TQ-01).
- Sau 4 tuần dùng thực tế (không tính tuần Tết): buổi đánh giá MVP với M-001 (đo lại 20 câu điển hình), M-002 (bộ câu hỏi kiểm thử), M-003, KR3.2 → mở rộng / điều chỉnh / dừng (OQ-022).
