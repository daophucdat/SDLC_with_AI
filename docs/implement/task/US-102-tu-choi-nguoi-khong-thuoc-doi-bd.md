# US-102 · Từ chối người không thuộc đội BD

| Thuộc tính | Giá trị |
|---|---|
| Loại | User story · E1. Truy cập |
| Sprint | Sprint 1 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | P0 |
| Story point | 3 `[Đề xuất]` |
| Vai trò thực hiện | Backend, Frontend, QA |
| Phụ thuộc | US-101, EN-09 (audit log) |
| Chặn bởi | — |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

> Là **quản lý**, tôi muốn người không thuộc đội BD bị từ chối truy cập, để tài liệu nội bộ không bị lộ.

**Truy vết:** BR-012, RUL-001 · UCD-02 · EC-18 · LG-10

**Thiết kế giao diện:** [`login.html?state=denied`](../../04-design/UI_UX_design/login.html?state=denied)

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** Những gì không được liệt kê ở mục 4 và mục 6.

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

**Bảng CSDL** (trích migration `0001_init`, dev_tasks.md §0.3)

```sql
CREATE TABLE platform.audit_log (
  id bigint GENERATED ALWAYS AS IDENTITY,
  ts timestamptz NOT NULL DEFAULT now(),
  actor_id uuid, action text NOT NULL, target_type text, target_id text, ip inet,
  PRIMARY KEY (id, ts)
) PARTITION BY RANGE (ts);
```

**Cấu hình**

| Biến | Mặc định |
|---|---|
| `ROLE_GROUP_MEMBER`, `ROLE_GROUP_LEAD`, `ROLE_GROUP_MANAGER` | `grp-bd-member`, `grp-bd-lead`, `grp-bd-manager` |

**Mã lỗi**

| code | HTTP | Thông điệp FE (`vi.ts`) | Hành động FE |
|---|---|---|---|
| AUTH_REQUIRED | 401 | — | Chuyển tới `/auth/login?returnTo=…`, giữ bản nháp |
| FORBIDDEN_ROLE | 403 | "Bạn chưa được cấp quyền dùng công cụ này. Liên hệ trưởng nhóm BD." | Trang `/denied` |

**Sự kiện phân tích** (danh sách cho phép, không có trường nội dung)

| name | Nguồn | props cho phép |
|---|---|---|
| `access_denied` | BE | `reason: enum` |

## 4. Công việc chi tiết

- [ ] **T102.1** `BE` — **Từ chối trong callback**: Không có nhóm hợp lệ → không tạo phiên; audit `access_denied`; sự kiện `access_denied`; 302 `/denied`
- [ ] **T102.2** `BE` — **`PermissionPolicy`**: `domain/access/permissions.py`: `can(user, action, resource=None) -> bool` với các action `documents:upload`, `documents:remove` (người tải lên hoặc LEAD), `metrics:view` (LEAD, MANAGER), `evaluation:run` (LEAD). Mọi application service đều gọi hàm này (không chỉ kiểm ở router)
- [ ] **T102.3** `BE` — **Mặc định từ chối**: Mọi router dưới `/api/v1` mặc định yêu cầu `CurrentUser`; route công khai phải khai báo rõ (danh sách cho phép: `/auth/*`, `/healthz`, `/readyz`)
- [ ] **T102.4** `FE` — **Trang `/denied`**: Theo `login.html?state=denied`; không gọi API nào khác
- [ ] **T102.5** `QA` — **Bộ test truy cập trái phép**: `backend/tests/security/test_unauthorized.py`: tham số hoá ≥ 20 ca (không cookie, cookie giả, phiên hết hạn, vai trò sai cho D4 / M1 / V1, CSRF sai…) → 100% bị từ chối (LG-10)

## 5. Trường hợp biên và lưu ý

- Xem các trường hợp lỗi ở mục 3 (mã lỗi) và các tiêu chí nghiệm thu ở mục 6.

## 6. Tiêu chí nghiệm thu

- [ ] **AC-102.1** — *Given* một tài khoản công ty không thuộc nhóm BD được cấp quyền, *When* người đó đăng nhập, *Then* họ thấy "Bạn chưa được cấp quyền dùng công cụ này. Liên hệ trưởng nhóm BD." và không thấy tên hay số lượng tài liệu.
- [ ] **AC-102.2** — *Given* một người chưa đăng nhập, *When* họ gọi trực tiếp API hoặc đường dẫn tài liệu, *Then* yêu cầu bị từ chối (`401`/`403`).
- [ ] **AC-102.3** — *Given* bộ ≥ 20 ca truy cập trái phép, *When* QA chạy, *Then* 100% bị từ chối (AC-012).

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Kiểm chứng AC-102.1 như mô tả ở mục 6 | Integration | AC-102.1 |
| Kiểm chứng AC-102.2 như mô tả ở mục 6 | Integration | AC-102.2 |
| Kiểm chứng AC-102.3 như mô tả ở mục 6 | Integration | AC-102.3 |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.
- [ ] Bộ test truy cập trái phép (≥ 20 ca) chạy trong CI; 100% bị từ chối (LG-10).

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
