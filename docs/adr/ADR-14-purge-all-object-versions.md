# ADR-14: Gỡ tài liệu xoá mọi phiên bản object; khôi phục phải áp lại lần gỡ

- Trạng thái: Accepted · Ngày: 2026-10-23 · Story: US-204, REL-02 · Yêu cầu: SEC-06

## Bối cảnh
Bucket bật versioning 7 ngày để khôi phục (SAD §4.2). Trên bucket có versioning, `DeleteObject` chỉ thêm *delete marker* — file PDF đã gỡ vẫn khôi phục được, vi phạm SEC-06 (xoá vĩnh viễn ≤ 24 giờ). Ngược lại, khôi phục CSDL về thời điểm trước một lần gỡ sẽ "hồi sinh" dòng tài liệu mà file đã mất.

## Quyết định
1. `S3DocumentStorage.delete` liệt kê và xoá **mọi phiên bản và delete marker** của key.
2. Worker ghi log `document_purged {document_id}` cho mỗi lần purge (giữ 30 ngày trên Loki).
3. Runbook khôi phục có bước bắt buộc chạy `infra/backup/reapply_removals.py` với danh sách id từ log đó.

## Hệ quả
- Tốt: SEC-06 đúng cả khi bucket có versioning.
- Xấu: tài liệu đã purge không thể khôi phục từ bucket — đúng ý đồ, nhưng phải ghi rõ trong runbook.
- Bản sao lưu CSDL vẫn có thể chứa văn bản đã trích của tài liệu đã gỡ tới 30 ngày (TQ-05 — chờ IT).

## Phương án đã cân nhắc
Lifecycle rule xoá phiên bản cũ sau N ngày — không đạt hạn 24 giờ.
