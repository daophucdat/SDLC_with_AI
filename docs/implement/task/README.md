# Bảng task — Chat với tài liệu (MVP)

Mỗi file là một task sẵn sàng phát triển, tách từ [implement_plan.md](../implement_plan.md). Chi tiết hợp đồng chung (CSDL, API, SSE, mã lỗi, sự kiện, prompt) ở [dev_tasks.md](../dev_tasks.md) Phần 0; story và tiêu chí nghiệm thu gốc ở [userStory.md](../userStory.md).

**Trạng thái hiện tại (2026-10-23):** mọi task có mã nguồn đã được hiện thực và qua test cục bộ → `In Review` (cần review PR + chạy trên môi trường thật, xem [reports/launch_gates.md](../reports/launch_gates.md)). REL-01 → REL-03 là công việc vận hành: hồ sơ / runbook / mẫu biên bản đã có trong [reports/](../reports/README.md).

**Quy trình:** nhận task → đổi `Trạng thái` thành In Progress và điền `Người nhận` → tạo nhánh `feat/<task-id>-<mô-tả>` (ví dụ `feat/US-201-upload`) → mở PR tham chiếu file task → tick checklist ở mục 4, 6, 8 → Done khi đạt Definition of Done.

**Tổng:** 37 task · 150 story point. EN-02 (8 điểm) được chia: 3 điểm ở Sprint 0 (môi trường dev), 5 điểm ở Sprint 1 (staging); điểm theo sprint bên dưới đã tính theo cách chia này. Sprint 4 gồm 22 điểm bắt buộc và 15 điểm P2 (chỉ làm khi còn năng lực).


## Sprint 0 · 16 điểm

| Task | Tên | Ưu tiên | Điểm | Vai trò | Phụ thuộc | Trạng thái |
|---|---|---|---|---|---|---|
| [EN-01](EN-01-khoi-tao-repo-va-ci.md) | Khởi tạo repo và CI | — | 3 | Backend, DevOps, QA | — | In Review |
| [EN-02](EN-02-ha-tang-va-moi-truong.md) | Hạ tầng và môi trường | — | 8 | Backend, DevOps | EN-01 | In Review |
| [EN-03](EN-03-dich-vu-embedder-benchmark.md) | Dịch vụ embedder + benchmark | — | 5 | AI engineer, Backend | EN-02 | In Review |
| [EN-11](EN-11-design-system-thanh-code.md) | Design system thành code | — | 5 | Frontend, QA | EN-01 | In Review |

## Sprint 1 · 29 điểm

| Task | Tên | Ưu tiên | Điểm | Vai trò | Phụ thuộc | Trạng thái |
|---|---|---|---|---|---|---|
| [US-101](US-101-dang-nhap-bang-tai-khoan-cong-ty.md) | Đăng nhập bằng tài khoản công ty | P0 | 5 | Backend, Frontend | EN-02 (OIDC client, secrets) | In Review |
| [US-102](US-102-tu-choi-nguoi-khong-thuoc-doi-bd.md) | Từ chối người không thuộc đội BD | P0 | 3 | Backend, Frontend, QA | US-101, EN-09 (audit log) | In Review |
| [US-201](US-201-tai-mot-hoac-nhieu-file-pdf.md) | Tải một hoặc nhiều file PDF | P0 | 5 | Backend, Frontend | EN-02 (storage), EN-11 (component UploadDropzone, DocumentItem) | In Review |
| [US-202](US-202-theo-doi-trang-thai-xu-ly-tung-file.md) | Theo dõi trạng thái xử lý từng file | P0 | 3 | Backend, Frontend | EN-04 (pipeline xử lý) | In Review |
| [EN-04](EN-04-pipeline-xu-ly-tai-lieu.md) | Pipeline xử lý tài liệu | — | 8 | AI engineer, Backend | EN-02, EN-03 | In Review |

## Sprint 2 · 37 điểm

| Task | Tên | Ưu tiên | Điểm | Vai trò | Phụ thuộc | Trạng thái |
|---|---|---|---|---|---|---|
| [EN-05](EN-05-truy-xuat-lai-chunkindex.md) | Truy xuất lai (ChunkIndex) | — | 8 | AI engineer, Backend, QA | EN-04 | In Review |
| [EN-06](EN-06-answergenerator-adapter.md) | AnswerGenerator adapter | — | 5 | AI engineer, Backend | EN-02 | In Review |
| [US-301](US-301-hoi-bang-tieng-viet-hoac-tieng-anh.md) | Hỏi bằng tiếng Việt hoặc tiếng Anh | P0 | 3 | Backend, Frontend | EN-11 (QuestionComposer) | In Review |
| [US-302](US-302-cau-tra-loi-tong-hop-tu-moi-tai-lieu-lien-quan.md) | Câu trả lời tổng hợp từ mọi tài liệu liên quan | P0 | 8 | AI engineer, Backend | EN-05 (truy xuất lai), EN-06 (LLM adapter), EN-10 (bộ câu hỏi kiểm thử) | In Review |
| [US-303](US-303-moi-y-co-trich-dan-tai-lieu-va-trang.md) | Mỗi ý có trích dẫn tài liệu và trang | P0 | 5 | Backend, Frontend | US-302 | In Review |
| [US-304](US-304-bao-ro-khong-tim-thay.md) | Báo rõ "không tìm thấy" | P0 | 5 | Backend, Frontend | EN-05, EN-10 (hiệu chỉnh `τ`) | In Review |
| [EN-10](EN-10-bo-cau-hoi-kiem-thu-va-harness-danh-gia.md) | Bộ câu hỏi kiểm thử và harness đánh giá | — | 3 | AI engineer, DevOps | EN-05, EN-06 (runner gọi API hỏi đáp) | In Review |

## Sprint 3 · 31 điểm

| Task | Tên | Ưu tiên | Điểm | Vai trò | Phụ thuộc | Trạng thái |
|---|---|---|---|---|---|---|
| [US-305](US-305-mo-dung-trang-nguon.md) | Mở đúng trang nguồn | P1 | 5 | Backend, Frontend, QA | US-303; endpoint file có Range (SAD §2.4) | In Review |
| [US-306](US-306-cau-tra-loi-hien-dan.md) | Câu trả lời hiện dần | P1 | 5 | Backend, Frontend, QA | US-302 | In Review |
| [US-310](US-310-dung-cau-tra-loi-dang-soan.md) | Dừng câu trả lời đang soạn | P1 | 3 | Backend, Frontend | US-306 | In Review |
| [US-203](US-203-xem-va-loc-danh-sach-tai-lieu.md) | Xem và lọc danh sách tài liệu | P1 | 3 | Backend, Frontend | US-201 | In Review |
| [US-204](US-204-go-tai-lieu.md) | Gỡ tài liệu | P1 | 5 | Backend, Frontend | US-203, EN-09 (job purge) | In Review |
| [US-205](US-205-bao-file-khong-doc-duoc-chu.md) | Báo file không đọc được chữ | P1 | 2 | Backend, Frontend, QA | EN-04 | In Review |
| [US-307](US-307-sao-chep-cau-tra-loi-kem-nguon.md) | Sao chép câu trả lời kèm nguồn | P1 | 2 | Frontend | US-303 | In Review |
| [US-309](US-309-danh-gia-cau-tra-loi.md) | Đánh giá câu trả lời | P1 | 3 | Backend, Frontend | EN-08 (sự kiện) | In Review |
| [EN-08](EN-08-su-kien-phan-tich.md) | Sự kiện phân tích | — | 3 | Backend | EN-02 | In Review |

## Sprint 4 · 37 điểm

| Task | Tên | Ưu tiên | Điểm | Vai trò | Phụ thuộc | Trạng thái |
|---|---|---|---|---|---|---|
| [US-103](US-103-tu-ket-thuc-phien-khi-khong-hoat-dong.md) | Tự kết thúc phiên khi không hoạt động | P1 | 2 | Backend, Frontend | US-101 | In Review |
| [US-401](US-401-trang-so-lieu-hang-tuan.md) | Trang số liệu hằng tuần | P1 | 5 | Backend, Frontend | EN-08 | In Review |
| [EN-07](EN-07-observability.md) | Observability | — | 5 | Backend, DevOps | EN-02 | In Review |
| [EN-09](EN-09-bao-mat-nen-tang.md) | Bảo mật nền tảng | — | 5 | Backend, DevOps, QA | US-101, EN-02 | In Review |
| [EN-12](EN-12-bo-test-e2e-va-test-hieu-nang.md) | Bộ test E2E và test hiệu năng | — | 5 | QA | Các story P0 / P1 cần kiểm thử | In Review |
| [US-206](US-206-canh-bao-file-trung.md) | Cảnh báo file trùng | P2 | 2 | Backend, Frontend | US-201 (tính mã băm nội dung) | In Review |
| [US-308](US-308-xem-lai-hoi-thoai-hien-tai.md) | Xem lại hội thoại hiện tại | P2 | 3 | Backend, Frontend | — | In Review |
| [US-311](US-311-hoi-tiep-theo-ngu-canh.md) | Hỏi tiếp theo ngữ cảnh | P2 | 5 | AI engineer, Backend | US-302, US-308 | In Review |
| [US-402](US-402-chay-bo-cau-hoi-kiem-thu-va-xuat-ket-qua.md) | Chạy bộ câu hỏi kiểm thử và xuất kết quả | P2 | 5 | Backend, Frontend | EN-10 (harness đánh giá) | In Review |

## Sprint 5 · 0 điểm

| Task | Tên | Ưu tiên | Điểm | Vai trò | Phụ thuộc | Trạng thái |
|---|---|---|---|---|---|---|
| [REL-01](REL-01-kiem-tra-toan-bo-dieu-kien-ra-mat-lg-01-lg-17.md) | Kiểm tra toàn bộ điều kiện ra mắt LG-01 → LG-17 | — | — | QA, Tech lead | Tất cả story P0 / P1 và enabler | To Do — hồ sơ đã chuẩn bị |
| [REL-02](REL-02-dien-tap-sao-luu-va-khoi-phuc.md) | Diễn tập sao lưu và khôi phục | — | — | DevOps | EN-02 | To Do — hồ sơ đã chuẩn bị |
| [REL-03](REL-03-uat-go-no-go-va-ra-mat-thu-nghiem.md) | UAT, Go / No-go và ra mắt thử nghiệm | — | — | PO / BA, Tech lead, Trưởng nhóm BD | REL-01, REL-02 | To Do — hồ sơ đã chuẩn bị |
