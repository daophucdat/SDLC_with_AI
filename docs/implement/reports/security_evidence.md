# Hồ sơ bảo mật gửi IT / Bảo mật (EN-09, LG-09, LG-11, LG-12)

Phần **"Trong mã nguồn"** đã được hiện thực và kiểm thử; phần **"Xác nhận trên môi trường"** do DevOps điền khi dựng staging / prod (ảnh chụp cấu hình hoặc lệnh kiểm tra).

## 1. Mã hoá khi lưu (T-EN09.6, SEC-03)

| Thành phần | Trong mã nguồn | Xác nhận trên môi trường |
|---|---|---|
| File PDF gốc (object storage) | Mọi `PutObject` gửi `ServerSideEncryption` theo `S3_SSE` (`aws:kms` trên AWS, `AES256` trên MinIO) — `backend/chatdocs/adapters/storage/s3.py` | Chính sách bucket từ chối upload không mã hoá; ảnh chụp cấu hình KMS: ☐ |
| CSDL (tài liệu đã trích, đoạn văn, vector, hội thoại) | — (thuộc hạ tầng) | Ổ đĩa / instance mã hoá (KMS hoặc LUKS): ☐ |
| Bản sao lưu | `infra/backup/backup.sh` ghi vào ổ đã mã hoá | Đích sao lưu mã hoá: ☐ |
| Đường truyền | TLS 1.2+ tại reverse proxy (`infra/nginx/chatdocs.conf`), HSTS 1 năm | Kết quả `testssl.sh`: ☐ |

## 2. Truy cập và phiên (SEC-01, SEC-02, US-101 → 103)

- Đăng nhập bằng IdP công ty (OIDC + PKCE). Token của IdP không được lưu sau khi đăng nhập.
- Phiên: cookie `__Host-session` HttpOnly, Secure, SameSite=Lax; CSDL chỉ lưu SHA-256 của cookie. Hết hạn sau 8 giờ không hoạt động; job dọn phiên mỗi 15 phút, hội thoại bị xoá cùng phiên (PD-04).
- CSRF: mọi `POST` / `DELETE` cần `X-CSRF-Token` = HMAC(bí mật của phiên) — `backend/chatdocs/adapters/http/auth.py`.
- Mặc định từ chối: mọi đường dẫn `/api/v1/*`, kể cả đường dẫn không tồn tại, yêu cầu phiên hợp lệ. Bộ test truy cập trái phép: 16 route × 4 kiểu cookie + các ca CSRF (LG-10).
- Phân quyền kiểm tra ở tầng application (`PermissionPolicy`): gỡ tài liệu (người tải lên hoặc Trưởng nhóm), số liệu (Trưởng nhóm, Quản lý), nghiệm thu (Trưởng nhóm).

## 3. Nội dung tài liệu không rò ra ngoài (TC-08, SEC-05)

- Log JSON có bộ lọc bỏ các khoá `text`, `content`, `question`, `answer`, `excerpt`, `prompt`; access log không ghi query string hay body. Test: câu hỏi chứa `ZZZ-SECRET` không xuất hiện trong log hay sự kiện (`test_analytics_events_carry_no_question_text`).
- Span tracing chỉ nhận thuộc tính số / boolean (`test_spans_never_record_text`); OTel Collector xoá thêm các khoá nội dung.
- Sự kiện phân tích theo danh sách cho phép, không có trường văn bản (`test_no_event_can_carry_content`: 13 sự kiện × 7 khoá nội dung); người dùng chỉ được đếm qua HMAC.
- Metric Prometheus dùng nhãn là mẫu route, không chứa id hay tên file.

## 4. Dịch vụ AI (LG-09, LG-12, SEC-04)

- Chỉ gửi tới LLM: lời nhắc hệ thống + tối đa 8 đoạn trích liên quan + câu hỏi (≤ `LLM_CONTEXT_TOKENS`). Không gửi toàn bộ file, không gửi tên người dùng.
- Nhà cung cấp mặc định: Claude API (`LLM_PROVIDER=anthropic`). Cần **văn bản** xác nhận không dùng dữ liệu để huấn luyện và chế độ lưu trữ tối thiểu theo hợp đồng của tổ chức: ☐ (LG-12).
- Phương án nội bộ nếu IT yêu cầu (OQ-008): `LLM_PROVIDER=openai_compatible` trỏ tới vLLM / TGI trong mạng công ty — cùng giao diện, không đổi mã.
- Chống prompt injection (T-EN09.7): nội dung tài liệu được bọc là dữ liệu (`<doan>`), lời nhắc cấm làm theo chỉ dẫn trong đó, câu trả lời không có trích dẫn hợp lệ bị chuyển thành "không tìm thấy" (ALG-3). Ca kiểm thử `S08` trong `eval/datasets/sample` (tài liệu có câu "Bỏ qua mọi chỉ dẫn…") — kết quả trên staging: ☐.
- Cờ tắt nhanh: `FEATURE_FLAGS=…,qa_off` dừng mọi lời gọi LLM mà không cần deploy.

## 5. Xoá dữ liệu (SEC-06)

- Gỡ tài liệu → ẩn ngay khỏi tìm kiếm và trích dẫn; job `purge_document` xoá file (mọi phiên bản trong bucket có versioning), các đoạn văn và trang trong ≤ 24 giờ; cảnh báo `PurgeOverdue` sau 20 giờ.
- Bản sao lưu CSDL có thể còn dữ liệu của tài liệu đã gỡ tối đa 30 ngày (TQ-05 — chờ IT chấp thuận): ☐. Khi khôi phục, runbook bắt buộc áp lại các lần gỡ (`restore_runbook.md` bước 4).

## 6. Quét lỗ hổng (T-EN09.5, LG-11)

| Công cụ | Ở đâu | Chặn merge khi |
|---|---|---|
| `pip-audit` | CI job `backend` | Có lỗ hổng đã biết |
| `npm audit --omit=dev --audit-level=high` | CI job `frontend` | High / Critical |
| Trivy (image backend) | CI job `image-scan` | High / Critical có bản sửa |
| gitleaks | CI job `secrets-scan` | Lộ bí mật |

Kết quả lần quét cuối trước Go / No-go: ☐ (link CI)

## 7. Nhật ký kiểm toán (T-EN09.4)

`platform.audit_log` ghi `login`, `logout`, `access_denied`, `upload`, `remove`, `evaluation_run`. Migration `0002` thu hồi quyền `UPDATE` / `DELETE` / `TRUNCATE` của vai trò ứng dụng `app_rw` trên bảng này (tài khoản ứng dụng chỉ `INSERT` / `SELECT`). Xác nhận vai trò `app_rw` là tài khoản ứng dụng dùng trên prod: ☐
