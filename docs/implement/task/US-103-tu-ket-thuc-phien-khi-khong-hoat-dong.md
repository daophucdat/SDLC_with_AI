# US-103 · Tự kết thúc phiên khi không hoạt động

| Thuộc tính | Giá trị |
|---|---|
| Loại | User story · E1. Truy cập |
| Sprint | Sprint 4 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | P1 |
| Story point | 2 `[Đề xuất]` |
| Vai trò thực hiện | Backend, Frontend |
| Phụ thuộc | US-101 |
| Chặn bởi | — |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

> Là **chuyên viên BD**, tôi muốn phiên tự kết thúc sau 8 giờ không hoạt động, để máy để quên không mở sẵn tài liệu cho người khác.

**Truy vết:** SN-007 · UCD-03 · PD-04 · `[PRD-new]` 8 giờ chờ PQ-005

**Thiết kế giao diện:** [`workspace.html?scenario=session`](../../04-design/UI_UX_design/workspace.html?scenario=session)

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** Những gì không được liệt kê ở mục 4 và mục 6.

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

**API**

| # | Endpoint | Request | Response 2xx | Lỗi (code) | Story |
|---|---|---|---|---|---|
| A3 | `POST /auth/logout` | — | 204 | — | US-103 |

**Bảng CSDL** (trích migration `0001_init`, dev_tasks.md §0.3)

```sql
CREATE TABLE access.session (
  id_hash bytea PRIMARY KEY,                -- sha256(cookie value)
  user_id uuid NOT NULL REFERENCES access.app_user(id),
  csrf_secret bytea NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  last_activity_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX ix_session_activity ON access.session (last_activity_at);
```

**Cấu hình**

| Biến | Mặc định |
|---|---|
| `SESSION_IDLE_HOURS` | `8` |

**Mã lỗi**

| code | HTTP | Thông điệp FE (`vi.ts`) | Hành động FE |
|---|---|---|---|
| AUTH_REQUIRED | 401 | — | Chuyển tới `/auth/login?returnTo=…`, giữ bản nháp |

## 4. Công việc chi tiết

- [ ] **T103.1** `BE` — **Hết hạn**: Đã có ở T101.5; thêm job `sweep_sessions` mỗi 15 phút: `DELETE FROM access.session WHERE last_activity_at < now() - interval ':h hours'` (cascade xoá hội thoại)
- [ ] **T103.2** `BE` — **`POST /auth/logout`**: Xoá phiên (cascade) + xoá cookie; audit `logout`
- [ ] **T103.3** `FE` — **Giữ bản nháp**: Interceptor 401 lưu bản nháp vào `sessionStorage`, hiện banner "Phiên đã hết hạn", nút "Đăng nhập lại" → `/auth/login?returnTo=…`; khôi phục bản nháp sau khi quay lại

## 5. Trường hợp biên và lưu ý

- Xem các trường hợp lỗi ở mục 3 (mã lỗi) và các tiêu chí nghiệm thu ở mục 6.

## 6. Tiêu chí nghiệm thu

- [ ] **AC-103.1** — *Given* phiên đã 8 giờ không có thao tác, *When* tôi thao tác tiếp, *Then* tôi được chuyển về đăng nhập.
- [ ] **AC-103.2** — *Given* tôi đang gõ dở một câu hỏi khi phiên hết hạn, *When* tôi đăng nhập lại, *Then* câu hỏi đang gõ vẫn còn (EC-17).
- [ ] **AC-103.3** — *Given* tôi đăng xuất, *When* phiên bị xoá, *Then* hội thoại của phiên cũng bị xoá (PD-04).

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Kiểm chứng AC-103.1 như mô tả ở mục 6 | Integration | AC-103.1 |
| Kiểm chứng AC-103.2 như mô tả ở mục 6 | Integration | AC-103.2 |
| Kiểm chứng AC-103.3 như mô tả ở mục 6 | Integration | AC-103.3 |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
