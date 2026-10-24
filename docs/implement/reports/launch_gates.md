# Điều kiện ra mắt LG-01 → LG-17 (REL-01)

Đầu vào cho họp Go / No-go (REL-03). Mỗi dòng cần **kết quả + bằng chứng + người xác nhận**. Cột "Công cụ trong repo" chỉ ra phần đã được hiện thực để thu bằng chứng; cột "Kết quả" chỉ điền khi đã chạy trên staging cấu hình như prod.

| LG | Nội dung | Ngưỡng | Công cụ trong repo (cách lấy bằng chứng) | Kết quả | Bằng chứng | Người xác nhận |
|---|---|---|---|---|---|---|
| LG-01 | Mọi AC của 8 story P0 đạt | 100% | CI: `backend` (pytest), `frontend` (vitest), `e2e` (Playwright `e2e/specs/f1-*`, `f2-*`, `f3-*`) | ⏳ | link báo cáo CI | QA |
| LG-02 | 0 lỗi Critical / High đang mở | 0 | Bug tracker | ⏳ | | QA |
| LG-03 | Đúng và đủ (câu cần ≥ 2 tài liệu) | ≥ 80% | `eval/run_eval.py` → `-grading.csv`, Trưởng nhóm BD chấm; hoặc US-402 trên trang Số liệu | ⏳ | | Trưởng nhóm BD |
| LG-04 | "Không tìm thấy" đúng | ≥ 9/10 | `eval/run_eval.py` (KR2.2, tự chấm) | ⏳ | | Trưởng nhóm BD |
| LG-05 | Trích dẫn đúng trang | ≥ 90% (mẫu 30) | `eval/run_eval.py` (KR2.3, khớp trang ± 0) + QA kiểm tay 30 trích dẫn | ⏳ | | QA |
| LG-06 | p95 thời gian trả lời | ≤ 30 s (phần đầu ≤ 5 s) | `k6 run e2e/perf/ask.js` (100 câu, 10 VU, 10 tài khoản) + dashboard Grafana | ⏳ | | QA |
| LG-07 | File 50 MB / 300 trang sẵn sàng | ≤ 5 phút | `eval/bench_embedder.py` (TQ-02) + upload thật; metric `doc_processing_seconds` | ⏳ | | QA |
| LG-08 | Mở màn hình chính | ≤ 3 s | `npx lhci autorun --config=e2e/lighthouserc.json` | ⏳ | | QA |
| LG-09 | IT phê duyệt xử lý tài liệu bằng dịch vụ AI | Văn bản | Hồ sơ `security_evidence.md` + OQ-008 | ⏳ | | IT / Bảo mật |
| LG-10 | Truy cập trái phép bị từ chối | 100% (≥ 20 ca) | `backend/tests/api/test_security_unauthorized.py` (16 route × 4 kiểu cookie + CSRF) — đạt trong CI | ✅ CI | job `backend` | QA |
| LG-11 | Mã hoá; 0 lỗ hổng Critical / High | 0 | CI: `pip-audit`, `npm audit --audit-level=high`, Trivy, gitleaks; `security_evidence.md` | ⏳ | | IT / Bảo mật |
| LG-12 | Cam kết không huấn luyện bằng văn bản | Văn bản | Hợp đồng / điều khoản nhà cung cấp AI | ⏳ | | IT / Bảo mật |
| LG-13 | 100% AC P0 / P1 có test case | 100% | Ma trận AC → test bên dưới | ⏳ | | QA |
| LG-14 | Hồi quy trên trình duyệt chuẩn | Pass | Playwright projects `chrome`, `edge` (PQ-004) | ⏳ | | QA |
| LG-15 | Mọi sự kiện PRD §5.2 được ghi | 13/13 | `backend/chatdocs/domain/analytics/events.py` (13 sự kiện, test `test_every_event_in_the_contract_is_listed`); kiểm tra trên staging: `SELECT name, count(*) FROM analytics.event GROUP BY 1` | ⏳ | | Engineering |
| LG-16 | Đã đo hiện trạng M-001 | Có số liệu | Trưởng nhóm BD bấm giờ 20 câu hỏi điển hình | ⏳ | | Trưởng nhóm BD |
| LG-17 | Cảnh báo gián đoạn trong giờ làm việc | Đội vận hành nhận được | `infra/observability/alerts.yml` (`ChatdocsUnreachable` P1, probe mỗi phút 08:00–18:00) — kích hoạt thử bằng cách dừng `api` | ⏳ | | Engineering |

✅ = đạt với bằng chứng · ⏳ = chưa chạy trên staging · ❌ = không đạt (ghi kế hoạch xử lý + ngày, hoặc lý do No-go)

## Ma trận AC P0 / P1 → test (LG-13)

| Story | AC | Test |
|---|---|---|
| US-101 | 101.1 · 101.2 · 101.3 | `web/src/auth/auth.test.tsx`; `backend/tests/api/test_auth_api.py`; `e2e/specs/f1-access.spec.ts` |
| US-102 | 102.1 · 102.2 · 102.3 | `auth.test.tsx` (denied, không gọi API); `test_security_unauthorized.py`; `f1-access.spec.ts` |
| US-103 | 103.1 · 103.2 · 103.3 | `test_auth_api.py` (hết hạn 8 giờ); `test_library_and_insights_api.py::test_idle_sessions_are_swept`; `chat.test.tsx` (bản nháp); `test_qa_api.py::test_logout_deletes_the_conversation_session` |
| US-201 | 201.1 · 201.2 | `library.test.tsx`; `uploadQueue.test.ts`; `test_documents_api.py`; `f2-library.spec.ts` |
| US-202 | 202.1 · 202.2 · 202.3 | `library.test.tsx` (polling, toast); `test_qa_api.py::test_processing_documents_are_counted_but_not_used`; `test_processing.py` |
| US-203 | 203.1 · 203.2 | `library-sprint3.test.tsx` (debounce, xoá bộ lọc); `f2-library.spec.ts` |
| US-204 | 204.1 → 204.5 | `test_library_and_insights_api.py` (quyền, purge, 403); `library-sprint3.test.tsx`; `test_qa_api.py::test_removed_document_is_never_cited` |
| US-205 | 205.1 · 205.2 | `test_processing.py::test_ten_scanned_pdfs_are_all_no_text`; `library-sprint3.test.tsx` |
| US-301 | 301.1 → 301.5 | `test_qa_domain.py`; `test_qa_api.py`; `chat.test.tsx`; `f3-qa.spec.ts` |
| US-302 | 302.1 · 302.2 · 302.3 | `test_qa_api.py` (2 tài liệu, tài liệu đã gỡ); 302.2 = LG-03 (người chấm) |
| US-303 | 303.1 → 303.4 | `test_qa_domain.py` (bảng ALG-3); `test_qa_api.py`; `chat.test.tsx`; 303.2 = LG-05 |
| US-304 | 304.1 → 304.4 | `test_qa_api.py` (NO_CHUNKS không gọi LLM); `chat.test.tsx`; 304.2 = LG-04 |
| US-305 | 305.1 · 305.2 · 305.3 | `chat.test.tsx` (mở, chuyển, Esc, 404); `test_library_and_insights_api.py::test_file_supports_range_requests`; `f3-qa.spec.ts` (≤ 2 s) |
| US-306 | 306.1 · 306.2 · 306.3 | `chat-units.test.ts` (máy trạng thái); `chat.test.tsx`; 306.1 = LG-06 (k6) |
| US-307 | 307.1 · 307.2 | `chat.test.tsx`; `f3-qa.spec.ts` |
| US-309 | 309.1 · 309.2 | `test_qa_api.py`; `chat.test.tsx`; `f3-qa.spec.ts` |
| US-310 | 310.1 · 310.2 | `test_qa_api.py::test_stop_*`; `chat.test.tsx`; `f3-qa.spec.ts` (fake LLM) |
| US-401 | 401.1 · 401.2 · 401.3 | `test_library_and_insights_api.py::test_metrics_*`; `test_insights_domain.py` (không có nội dung); `metrics.test.tsx`; `f5-metrics.spec.ts` |
