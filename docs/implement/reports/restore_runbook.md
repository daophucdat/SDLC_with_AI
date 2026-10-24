# Runbook khôi phục — Chat với tài liệu (REL-02)

| Thuộc tính | Giá trị |
|---|---|
| Mục tiêu | RTO ≤ 4 giờ (dựng lại toàn bộ), RPO ≤ 24 giờ (thực tế ≈ 5 phút nhờ PITR) — SAD §4.2 |
| Áp dụng | Staging (diễn tập mỗi quý) và prod (sự cố thật) |
| Người thực hiện | DevOps trực; người phê duyệt: Tech lead |
| Công cụ | `infra/backup/*`, IaC của môi trường, `alembic`, `psql`, `mc` (MinIO client) hoặc `aws s3api` |

> Nguyên tắc: **không bao giờ khôi phục đè lên CSDL đang chạy.** Luôn khôi phục vào máy/instance mới, kiểm tra, rồi mới chuyển hướng ứng dụng.

## 0. Quyết định thời điểm khôi phục

1. Xác định thời điểm cuối cùng dữ liệu còn đúng (giờ Việt Nam, ví dụ `2027-01-12 09:30:00+07`).
2. Ghi vào biên bản: lý do, thời điểm, người phê duyệt.
3. Bật cờ dừng hỏi đáp để người dùng không tạo dữ liệu mới trong lúc khôi phục: `FEATURE_FLAGS=…,qa_off` rồi khởi động lại `api` (banner "Hỏi đáp tạm gián đoạn" hiện cho người dùng).

## 1. Ghi lại trạng thái hiện tại (nếu hệ thống còn đọc được)

```bash
psql "$DATABASE_URL_PSQL" -f infra/backup/capture_state.sql > state-before.txt
```

Ghi thêm một câu hỏi mẫu kèm câu trả lời và trích dẫn (tài liệu, trang) — dùng để so sánh ở bước 6.

## 2. Khôi phục PostgreSQL về thời điểm (PITR)

*CSDL được quản lý (RDS / Cloud SQL):* dùng chức năng "restore to point in time" của nhà cung cấp, tạo instance mới, chuyển sang bước 3.

*CSDL tự quản lý:*

```bash
./infra/backup/restore_pitr.sh LATEST "2027-01-12 09:30:00+07" /var/lib/postgresql/16/restore
# khởi động PostgreSQL trên thư mục trên, chờ log "database system is ready to accept connections"
DATABASE_URL=… alembic current        # phải in revision head (hiện tại: 0002)
```

Thời gian ghi nhận: ____ phút.

## 3. Khôi phục object storage

Bucket `chat-docs` bật versioning 7 ngày. Khôi phục mọi object về phiên bản tại thời điểm đã chọn:

```bash
mc alias set prod https://s3.… "$S3_ACCESS_KEY" "$S3_SECRET_KEY"
mc cp --recursive --rewind "2027-01-12T09:30:00+07:00" prod/chat-docs/ restore/chat-docs/
```

**SEC-06:** tài liệu đã bị *purge* (gỡ và xoá vĩnh viễn) không thể và không được khôi phục — job purge xoá mọi phiên bản. Bước 4 xử lý phần CSDL tương ứng.

Thời gian ghi nhận: ____ phút.

## 4. Áp lại các lần gỡ tài liệu sau thời điểm khôi phục (bắt buộc)

CSDL khôi phục về trước một lần gỡ sẽ "hồi sinh" dòng tài liệu (READY) trong khi file đã bị xoá. Lấy danh sách tài liệu đã purge từ log của worker (Loki giữ 30 ngày):

```
{service="worker"} |= "document_purged" | json | line_format "{{.document_id}}"
```

Khoảng thời gian: từ thời điểm khôi phục tới hiện tại. Lưu thành `purged_ids.txt` rồi:

```bash
DATABASE_URL=postgresql+asyncpg://…(CSDL mới) python infra/backup/reapply_removals.py purged_ids.txt
```

Kiểm tra: `SELECT count(*) FROM documents.document WHERE id = ANY(…) AND status <> 'REMOVED'` = 0.

## 5. Dựng lại `api`, `worker`, `embedder`

1. Chạy IaC của môi trường (Compose + Ansible hoặc Terraform) với `DATABASE_URL` và bucket mới.
2. `api` chạy `alembic upgrade head` khi khởi động (không làm gì nếu đã ở head).
3. Kiểm tra `GET /readyz` = 200 với `database`, `storage`, `embedder` đều `true`.
4. Bỏ cờ `qa_off`, khởi động lại `api`.

Thời gian ghi nhận: ____ phút.

## 6. Kiểm chứng

```bash
psql "$DATABASE_URL_PSQL" -f infra/backup/capture_state.sql > state-after.txt
diff state-before.txt state-after.txt
```

- Số tài liệu theo trạng thái và `chunk_fingerprint` khớp với trạng thái tại thời điểm khôi phục (khác biệt chỉ do bước 4).
- Câu hỏi mẫu cho cùng câu trả lời, cùng tài liệu và trang được trích dẫn.
- Đăng nhập bằng 1 tài khoản Thành viên và 1 tài khoản Trưởng nhóm; mở một trang nguồn.
- Phiên cũ của người dùng có thể đã mất (bảng `access.session` theo thời điểm khôi phục) — họ chỉ cần đăng nhập lại.

## 7. Biên bản diễn tập

| Bước | Bắt đầu | Kết thúc | Thời lượng | Ghi chú |
|---|---|---|---|---|
| 1. Ghi trạng thái | | | | |
| 2. PITR CSDL | | | | |
| 3. Object storage | | | | |
| 4. Áp lại lần gỡ | | | | |
| 5. Dựng lại dịch vụ | | | | |
| 6. Kiểm chứng | | | | |
| **Tổng (≤ 4 giờ)** | | | | |

RPO đo được (thời điểm khôi phục → bản ghi cuối cùng có trong CSDL mới): ____ · Người thực hiện: ____ · Người không tham gia diễn tập đã đọc và làm theo được: ____

## Sự cố truy cập

Cảnh báo `ChatdocsUnreachable` (P1): kiểm tra theo thứ tự → reverse proxy / chứng chỉ TLS → `GET /healthz` từng bản sao `api` → `GET /readyz` (CSDL, storage, embedder) → log `api` trên Loki theo `trace_id`. LLM lỗi **không** làm hệ thống "không truy cập được" (không nằm trong readyz); khi đó cảnh báo là `LlmCircuitOpen` và người dùng thấy banner.
