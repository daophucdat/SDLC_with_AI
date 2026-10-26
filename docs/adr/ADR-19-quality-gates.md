# ADR-19: Ngưỡng cổng chất lượng L0

- Trạng thái: Accepted · Ngày: 2026-10-26 · Story: EN-01 · Nguồn: Day 5 — "Cổng chất lượng tự động (L0)", "Đo chất lượng và cái bẫy"

## Quyết định

| Cổng | Ngưỡng chặn merge | Công cụ | Job CI |
|---|---|---|---|
| Format + lint | 0 lỗi, 0 cảnh báo | ruff, black · eslint `--max-warnings 0`, prettier | `backend`, `frontend` |
| Type check | 0 lỗi | `tsc --noEmit` | `frontend` |
| Độ phức tạp | ≤ 10 mỗi hàm | ruff `C901` · eslint `complexity` | `backend`, `frontend` |
| Kiến trúc | 4 hợp đồng import (DR-1 → DR-5) | import-linter | `backend` |
| Test | 100% pass | pytest (kể cả tích hợp PostgreSQL), vitest | `backend`, `frontend` |
| Coverage | ≥ 70% toàn bộ; ≥ 90% module lõi (domain, Q&A, truy xuất) | pytest-cov, vitest v8 | `backend`, `frontend` |
| Trùng lặp | < 3% | jscpd | `quality` |
| Secret | 0 trong diff | gitleaks | `secrets-scan` |
| Phụ thuộc | 0 CVE high / critical; SBOM | pip-audit, npm audit, Trivy · CycloneDX | `backend`, `frontend`, `image-scan` |
| Build | tái lập được, < 10 phút | `timeout-minutes: 10`, artifact | mọi job |
| Truy vết | mỗi commit có US/EN/REL/BR; ma trận khớp code | `scripts/check_traceability.py` | `traceability` |
| Mutation (không chặn merge) | ≥ 60% module lõi | mutmut (hằng tuần) | `mutation.yml` |

## Lý do
- Coverage chỉ nói "dòng đã chạy", không nói "đã kiểm tra đúng" → thêm mutation score cho module lõi; chạy hằng tuần vì chậm.
- Lớp rẻ chạy trước và phải nhanh: một job quá 10 phút bị coi là lỗi cổng.

## Hệ quả
- Tại thời điểm quyết định: backend coverage 76% (96% lõi), web 95,6%; trùng lặp 0,13%; độ phức tạp sau refactor ≤ 10; mutation score lõi 58% → 94,7% sau khi thêm `tests/unit/test_core_contracts.py`.
- Commit `3875cc0` (trước khi có cổng) không có mã yêu cầu — ghi trong `docs/quality/escaped_defects.md`; cổng chỉ kiểm commit mới.
