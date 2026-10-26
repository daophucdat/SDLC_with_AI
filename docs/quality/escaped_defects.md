# Lỗi lọt (escaped defects)

Day 5 — "Escaped defects: lỗi lọt review, theo tháng". Ghi mọi lỗi được phát hiện **sau** khi code đã qua review hoặc đã vào `main`, kể cả lỗi tìm thấy bởi cổng mới. Mục đích: biết lớp nào của tháp chất lượng (L0 → L4) đã bỏ sót, rồi thêm kiểm tra cho lớp đó.

| Ngày | Mô tả | Lọt qua lớp | Phát hiện bởi | Sửa / kiểm tra thêm | Story |
|---|---|---|---|---|---|
| 2026-10-23 | `DeleteObject` trên bucket có versioning chỉ thêm delete marker → PDF đã gỡ vẫn khôi phục được (vi phạm SEC-06) | L2 (thiết kế ban đầu không xét versioning) | Đọc lại khi viết runbook | Xoá mọi phiên bản; ADR-14 | US-204 |
| 2026-10-24 | API container không gọi được Keycloak qua `localhost` → đăng nhập hỏng trong docker compose | L0 (không có E2E trên compose) | Đọc lại cấu hình trước khi thêm job E2E | `OIDC_INTERNAL_BASE_URL`; ADR-15; job `e2e` | US-101 |
| 2026-10-24 | nginx bỏ header bảo mật ở location có `add_header` riêng | L2 | Review cấu hình | Include chung `chatdocs-security-headers.conf` | EN-09 |
| 2026-10-26 | Commit `3875cc0` không có mã US/EN — trước khi có cổng truy vết | L0 (cổng chưa tồn tại) | `scripts/check_traceability.py` | Cổng `traceability` trong CI, chỉ kiểm commit mới | EN-01 |
| 2026-10-26 | Ngưỡng coverage web viết theo cú pháp vitest 1.x (`thresholds: {}`) trong khi dự án dùng 0.34 → ngưỡng bị bỏ qua, cổng 70% không chặn gì; commit `a8fb18b` lọt vì chưa chạy `typecheck` trước khi commit | L0 (chạy thiếu cổng trước commit) | `scripts/dev.sh check` (tsc báo lỗi) | Sửa cú pháp; kiểm chứng cổng **có thể đỏ** (`--coverage.lines=99` → lỗi) | EN-01 |
| 2026-10-26 | Mutation score module lõi 58% (< 60%) dù coverage 96%: thiếu assertion cho công thức RRF, ranh giới τ, giá trị hợp đồng của enum, tính bất biến của value object | L1/L2 (test viết theo luồng chính) | mutmut | `tests/unit/test_core_contracts.py` → 94,7% (124 giết / 7 sống, các mutant còn lại tương đương: chú thích kiểu, `@staticmethod`); job `mutation.yml` hằng tuần | US-302, US-303, US-304 |

## Tổng hợp theo tháng

| Tháng | Số lỗi lọt | L0 | L1 | L2 | L3 | L4 |
|---|---|---|---|---|---|---|
| 2026-10 | 6 | 3 | 1 | 3 | 0 | 0 |

(Một lỗi có thể lọt qua nhiều lớp.)
