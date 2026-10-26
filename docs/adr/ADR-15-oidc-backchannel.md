# ADR-15: URL IdP nội bộ cho lời gọi server-to-server

- Trạng thái: Accepted · Ngày: 2026-10-24 · Story: US-101, EN-02

## Bối cảnh
Trong docker compose, trình duyệt gọi Keycloak qua `http://localhost:8080`, nhưng `localhost` trong container API là chính nó: discovery, đổi code lấy token và JWKS đều thất bại. Token phải mang `iss` giống nhau dù yêu cầu đến từ đâu.

## Quyết định
- Thêm `OIDC_INTERNAL_BASE_URL` (ví dụ `http://keycloak:8080`). `OidcProvider` thay origin công khai bằng origin nội bộ cho discovery, token và JWKS; URL chuyển hướng trình duyệt và `iss` mong đợi giữ nguyên.
- Keycloak dev chạy với `--hostname=http://localhost:8080 --hostname-backchannel-dynamic=true` để `iss` cố định.

## Hệ quả
- Tốt: cùng một cấu hình cho dev, CI E2E và prod (prod để trống biến này).
- Phải làm: test `test_oidc_backchannel_uses_internal_base_url`.

## Phương án đã cân nhắc
`network_mode: host` — không chạy được trên Docker Desktop Windows/macOS; `extra_hosts` trỏ localhost — gây nhầm lẫn và hỏng các dịch vụ khác.
