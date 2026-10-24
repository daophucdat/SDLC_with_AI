# US-101 · Đăng nhập bằng tài khoản công ty

| Thuộc tính | Giá trị |
|---|---|
| Loại | User story · E1. Truy cập |
| Sprint | Sprint 1 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | P0 |
| Story point | 5 `[Đề xuất]` |
| Vai trò thực hiện | Backend, Frontend |
| Phụ thuộc | EN-02 (OIDC client, secrets) |
| Chặn bởi | DEP-002 (IdP công ty, ánh xạ nhóm → vai trò) |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

> Là **chuyên viên BD**, tôi muốn đăng nhập bằng tài khoản công ty do IT cấp, để không phải nhớ thêm mật khẩu riêng.

**Truy vết:** BR-012 · UCD-01, UCD-02 · SEC-01 · LG-10 · màn hình `login.html`

**Thiết kế giao diện:** [`login.html`](../../04-design/UI_UX_design/login.html)

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** Đồng bộ thay đổi nhóm của IdP trong khi phiên còn hiệu lực (DQ-03).

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

**API**

| # | Endpoint | Request | Response 2xx | Lỗi (code) | Story |
|---|---|---|---|---|---|
| A1 | `GET /auth/login?returnTo=/` | — | 302 → IdP | — | US-101 |
| A2 | `GET /auth/callback?code&state` | — | 302 → `returnTo`; đặt `__Host-session` + `__Host-csrf` | 302 → `/denied` (FORBIDDEN_ROLE); 302 → `/login?error=idp` | US-101, 102 |
| A4 | `GET /api/v1/me` | — | `{id, displayName, role, permissions: ["documents:remove_any"?, "metrics:view"?, "evaluation:run"?], flags: [..]}` | 401 AUTH_REQUIRED | US-101 |

**Bảng CSDL** (trích migration `0001_init`, dev_tasks.md §0.3)

```sql
CREATE UNIQUE INDEX ux_user_email ON access.app_user (lower(email));

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
| `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_REDIRECT_URI` | — |
| `OIDC_GROUPS_CLAIM` | `groups` |
| `ROLE_GROUP_MEMBER`, `ROLE_GROUP_LEAD`, `ROLE_GROUP_MANAGER` | `grp-bd-member`, `grp-bd-lead`, `grp-bd-manager` |

**Mã lỗi**

| code | HTTP | Thông điệp FE (`vi.ts`) | Hành động FE |
|---|---|---|---|
| AUTH_REQUIRED | 401 | — | Chuyển tới `/auth/login?returnTo=…`, giữ bản nháp |

**Sự kiện phân tích** (danh sách cho phép, không có trường nội dung)

| name | Nguồn | props cho phép |
|---|---|---|
| `session_started` | BE (callback) | `is_first_session: bool` |

## 4. Công việc chi tiết

- [ ] **T101.1** `BE` — **Port + adapter OIDC**: `ports/identity.py`: `IdentityProvider.build_auth_url(state, nonce, code_challenge)`, `exchange_code(code, verifier) -> IdTokenClaims`. `adapters/oidc/generic.py` dùng `authlib`: discovery, JWKS cache 1 giờ, kiểm tra `iss`, `aud`, `exp`, `nonce`
- [ ] **T101.2** `BE` — **`GET /auth/login`**: Sinh `state`, `nonce`, `code_verifier` (PKCE S256); lưu vào cookie tạm `__Host-oidc` (ký HMAC, sống 10 phút); 302 tới IdP. Chỉ chấp nhận `returnTo` là đường dẫn tương đối (chống open redirect)
- [ ] **T101.3** `BE` — **`GET /auth/callback`**: Kiểm tra `state`; đổi code lấy token; `AccessService.login(claims)`: ánh xạ nhóm → vai trò (`domain/access/role_mapping.py`, ưu tiên LEAD > MANAGER > MEMBER); upsert `app_user`; tạo phiên; ghi audit `login`; sự kiện `session_started`
- [ ] **T101.4** `BE` — **Tạo phiên**: Giá trị cookie = 32 byte `secrets.token_bytes` → base64url; lưu `sha256` vào `session.id_hash`; `csrf_secret` 32 byte. Cookie: `__Host-session` (HttpOnly, Secure, SameSite=Lax, Path=/), `__Host-csrf` (không HttpOnly, để FE đọc)
- [ ] **T101.5** `BE` — **Middleware xác thực**: `adapters/http/auth.py`: tra phiên theo PK; nếu `now - last_activity_at > SESSION_IDLE_HOURS` → xoá phiên, trả 401; cập nhật `last_activity_at` tối đa 1 lần / phút; gắn `CurrentUser` vào request
- [ ] **T101.6** `BE` — **`GET /api/v1/me`**: Trả `id`, `displayName`, `role`, `permissions` (từ `PermissionPolicy`), `flags`
- [ ] **T101.7** `FE` — **`RequireAuth` + trang login**: Gọi `/me`; gặp 401 thì chuyển tới `/auth/login?returnTo=<đường dẫn hiện tại>`; `/login?error=idp` hiện trạng thái "IdP lỗi" như `login.html?state=error`; header hiện tên và vai trò

**Trường hợp biên:** user bị IT gỡ khỏi nhóm khi đang có phiên → lần đăng nhập sau bị từ chối (MVP chấp nhận phiên hiện tại sống tới khi hết hạn; ghi vào known issues). Email đổi chữ hoa / thường → so khớp theo `lower(email)`.

## 5. Trường hợp biên và lưu ý

- Xem các trường hợp lỗi ở mục 3 (mã lỗi) và các tiêu chí nghiệm thu ở mục 6.

## 6. Tiêu chí nghiệm thu

- [ ] **AC-101.1** — *Given* tôi là thành viên BD đã được IT cấp quyền, *When* tôi mở đường dẫn và đăng nhập bằng tài khoản công ty, *Then* tôi vào màn hình làm việc trong ≤ 5 giây và thấy tên của mình.
- [ ] **AC-101.2** — *Given* tôi đã đăng nhập, *When* tôi đóng tab rồi mở lại khi phiên còn hiệu lực, *Then* tôi không phải đăng nhập lại.
- [ ] **AC-101.3** — *Given* hệ thống tài khoản công ty không phản hồi, *When* tôi đăng nhập, *Then* tôi thấy thông báo "chưa đăng nhập được" kèm nút thử lại.

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Đăng nhập Keycloak với user `grp-bd-member` → vào `/` ≤ 5 s, thấy tên | E2E | AC-101.1 |
| Đóng mở lại tab khi phiên còn hạn → không chuyển hướng | E2E | AC-101.2 |
| IdP trả lỗi / không phản hồi → `/login?error=idp` có nút thử lại | Integration (mock IdP) | AC-101.3 |
| `state` sai, `nonce` sai, token hết hạn → từ chối | Unit | bảo mật |
| `returnTo=https://evil.com` → bị thay bằng `/` | Unit | bảo mật |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
