# Ma trận truy vết — US ↔ BR/UCD ↔ code ↔ test

Dự án dùng mã yêu cầu nghiệp vụ **BR-xxx** (BRD / PRD §4) và use case **UCD-xx** thay cho "FR". Mỗi dòng chỉ ra mã nguồn chính và test chứng minh AC. `python scripts/check_traceability.py matrix` (chạy trong CI) kiểm tra: mọi US trong `docs/implement/userStory.md` có mặt ở đây và mọi đường dẫn trong bảng tồn tại.

Cập nhật bảng này **cùng commit** với thay đổi code / test của story (AGENTS.md).

## Story P0 / P1 / P2

| US | BR / UCD / NFR | Code chính | Test (AC) |
|---|---|---|---|
| US-101 | BR-012 · UCD-01, 02 · SEC-01 | `backend/chatdocs/application/access_service.py`, `backend/chatdocs/adapters/http/routes_auth.py`, `backend/chatdocs/adapters/oidc/generic.py`, `web/src/auth/RequireAuth.tsx`, `web/src/pages/LoginPage.tsx` | `backend/tests/api/test_auth_api.py`, `web/src/auth/auth.test.tsx`, `e2e/specs/f1-access.spec.ts` |
| US-102 | BR-012, RUL-001 · UCD-02 · EC-18 · LG-10 | `backend/chatdocs/domain/access/role_mapping.py`, `backend/chatdocs/domain/access/permissions.py`, `backend/chatdocs/adapters/http/auth.py` | `backend/tests/api/test_security_unauthorized.py`, `web/src/auth/auth.test.tsx` |
| US-103 | SN-007 · UCD-03 · PD-04 | `backend/chatdocs/application/access_service.py`, `backend/chatdocs/application/maintenance.py`, `web/src/pages/WorkspacePage.tsx`, `web/src/chat/QuestionComposer.tsx` | `backend/tests/api/test_auth_api.py::test_idle_session_expires_after_8_hours`, `backend/tests/api/test_library_and_insights_api.py::test_idle_sessions_are_swept`, `web/src/chat/chat.test.tsx` |
| US-201 | BR-001 · UCD-04, 05 · NFR-06 | `backend/chatdocs/application/document_service.py`, `backend/chatdocs/domain/documents/upload_policy.py`, `backend/chatdocs/adapters/http/routes_api.py`, `web/src/features/library/uploadQueue.ts`, `web/src/features/library/LibraryPanel.tsx` | `backend/tests/api/test_documents_api.py`, `web/src/features/library/uploadQueue.test.ts`, `web/src/features/library/library.test.tsx`, `e2e/specs/tc-us201.spec.ts` (TC-201-01…13) |
| US-202 | BR-001 · UCD-06, 09 · NFR-03 | `backend/chatdocs/application/document_processing_service.py`, `backend/chatdocs/adapters/jobs/runner.py`, `web/src/features/library/useDocuments.ts` | `backend/tests/unit/test_processing.py`, `backend/tests/unit/test_job_runner.py`, `web/src/features/library/library.test.tsx` |
| US-203 | BR-004 · UCD-10, 14 | `backend/chatdocs/adapters/db/repositories.py`, `web/src/features/library/LibraryPanel.tsx` | `backend/tests/api/test_documents_api.py`, `web/src/features/library/library-sprint3.test.tsx` |
| US-204 | BR-005, RUL-003 · UCD-11 → 13, 15 · SEC-06 | `backend/chatdocs/application/document_service.py`, `backend/chatdocs/adapters/storage/s3.py`, `backend/chatdocs/adapters/jobs/worker_main.py`, `web/src/features/library/LibraryPanel.tsx` | `backend/tests/api/test_library_and_insights_api.py`, `backend/tests/api/test_qa_api.py::test_removed_document_is_never_cited`, `web/src/features/library/library-sprint3.test.tsx` |
| US-205 | BR-006 · UCD-07 · EC-10 | `backend/chatdocs/domain/documents/text_cleanup.py`, `backend/chatdocs/application/document_processing_service.py` | `backend/tests/unit/test_processing.py::test_ten_scanned_pdfs_are_all_no_text`, `web/src/features/library/library-sprint3.test.tsx` |
| US-206 | SN-006 · UCD-08 · EC-12 | `backend/chatdocs/application/document_service.py`, `web/src/features/library/LibraryPanel.tsx` | `backend/tests/api/test_documents_api.py`, `web/src/features/library/library.test.tsx` |
| US-301 | BR-002 · UCD-16 | `backend/chatdocs/domain/qa/question.py`, `backend/chatdocs/adapters/http/routes_qa.py`, `web/src/chat/QuestionComposer.tsx`, `web/src/chat/useAsk.ts`, `web/src/api-client/sse.ts` | `backend/tests/unit/test_qa_domain.py`, `backend/tests/api/test_qa_api.py`, `web/src/chat/chat.test.tsx`, `e2e/specs/tc-us303.spec.ts` (TC-303-01…10) |
| US-302 | BR-003 · UCD-19 · ALG-2 · LG-03 | `backend/chatdocs/application/qa_service.py`, `backend/chatdocs/application/retrieval_service.py`, `backend/chatdocs/domain/qa/prompt.py`, `backend/chatdocs/adapters/llm/anthropic_adapter.py` | `backend/tests/api/test_qa_api.py::test_answer_can_cite_two_documents`, `backend/tests/unit/test_retrieval.py`, `eval/run_eval.py` |
| US-303 | BR-007 · UCD-20 · ALG-3 · LG-05 | `backend/chatdocs/domain/qa/citation_policy.py`, `web/src/chat/AnswerCard.tsx` | `backend/tests/unit/test_qa_domain.py`, `backend/tests/api/test_qa_api.py`, `web/src/chat/chat.test.tsx`, `e2e/specs/tc-us303.spec.ts` (TC-303-01…10) |
| US-304 | BR-008, RUL-002 · UCD-21 · LG-04 | `backend/chatdocs/domain/retrieval/rrf.py`, `backend/chatdocs/application/qa_service.py`, `web/src/chat/AnswerCard.tsx` | `backend/tests/api/test_qa_api.py::test_no_matching_chunks_is_not_found_without_calling_the_llm`, `web/src/chat/chat.test.tsx` |
| US-305 | BR-007, SN-005 · UCD-22 · NFR-05 | `backend/chatdocs/adapters/http/routes_api.py`, `web/src/source-viewer/SourcePanel.tsx`, `web/src/source-viewer/pdf.ts` | `backend/tests/api/test_library_and_insights_api.py::test_file_supports_range_requests`, `web/src/chat/chat.test.tsx`, `e2e/specs/f3-qa.spec.ts` |
| US-306 | BR-009 · UCD-19 · NFR-02 | `web/src/chat/answerMachine.ts`, `web/src/chat/useAsk.ts`, `backend/chatdocs/adapters/http/routes_qa.py` | `web/src/chat/chat-units.test.ts`, `web/src/chat/chat.test.tsx`, `e2e/perf/ask.js` |
| US-307 | SN-001 · UCD-24 | `web/src/chat/AnswerCard.tsx` | `web/src/chat/chat.test.tsx` |
| US-308 | BR-010 · UCD-18 · PD-04 | `backend/chatdocs/adapters/db/qa_repository.py`, `web/src/state/chatStore.ts` | `backend/tests/api/test_qa_api.py::test_history_is_private_to_the_session`, `web/src/chat/chat.test.tsx` |
| US-309 | PD-03 · KR3.2 · UCD-25 | `backend/chatdocs/application/qa_service.py`, `web/src/chat/AnswerCard.tsx` | `backend/tests/api/test_qa_api.py::test_feedback_once_and_only_on_completed_answers`, `web/src/chat/chat.test.tsx` |
| US-310 | BR-009 · UCD-23 | `backend/chatdocs/application/qa_service.py`, `backend/chatdocs/adapters/db/qa_repository.py`, `web/src/chat/useAsk.ts` | `backend/tests/api/test_qa_api.py::test_stop_cancels_generation_and_keeps_partial_text`, `web/src/chat/chat.test.tsx` |
| US-311 | BR-010, SN-001 · UCD-17 | `backend/chatdocs/domain/qa/prompt.py`, `web/src/chat/QuestionComposer.tsx` | `backend/tests/unit/test_qa_domain.py::test_follow_up_uses_at_most_two_previous_turns`, `backend/tests/api/test_qa_api.py::test_follow_up_uses_history_only_when_flag_is_on` |
| US-401 | SN-002 · UCD-26 · M-003 | `backend/chatdocs/domain/metrics/weekly.py`, `backend/chatdocs/application/insights_service.py`, `web/src/metrics/MetricsPage.tsx` | `backend/tests/unit/test_insights_domain.py`, `backend/tests/api/test_library_and_insights_api.py`, `web/src/metrics/metrics.test.tsx` |
| US-402 | UC-05 · UCD-27, 28 · M-002 | `backend/chatdocs/domain/evaluation/test_set.py`, `backend/chatdocs/adapters/xlsx/testset_xlsx.py`, `web/src/metrics/MetricsPage.tsx` | `backend/tests/unit/test_insights_domain.py`, `backend/tests/api/test_library_and_insights_api.py::test_evaluation_flow`, `web/src/metrics/metrics.test.tsx` |

## Enabler

| EN | Nội dung | Code / cấu hình | Bằng chứng |
|---|---|---|---|
| EN-01 | Repo, CI, cổng chất lượng | `.github/workflows/ci.yml`, `scripts/check_traceability.py` | log CI |
| EN-02 | Hạ tầng | `infra/docker-compose.yml`, `backend/migrations/versions/0001_init.py` | `backend/tests/integration/test_postgres.py` |
| EN-03 | Embedder | `backend/chatdocs/adapters/embedder/tei.py`, `eval/bench_embedder.py` | `backend/tests/unit/test_tei_embedder.py` |
| EN-04 | Pipeline xử lý | `backend/chatdocs/domain/documents/chunking.py` | `backend/tests/unit/test_text_and_chunking.py` |
| EN-05 | Truy xuất lai | `backend/chatdocs/adapters/pgvector/chunk_index.py` | `backend/tests/unit/test_retrieval.py` |
| EN-06 | LLM adapter | `backend/chatdocs/adapters/llm/resilient.py`, `backend/chatdocs/platform/circuit_breaker.py` | `backend/tests/unit/test_platform_resilience.py`, `backend/tests/unit/test_llm_adapters.py` |
| EN-07 | Observability | `backend/chatdocs/platform/metrics.py`, `infra/observability/alerts.yml` | `backend/tests/api/test_library_and_insights_api.py::test_prometheus_metrics_have_bounded_labels` |
| EN-08 | Sự kiện | `backend/chatdocs/domain/analytics/events.py`, `backend/chatdocs/adapters/analytics/postgres_sink.py` | `backend/tests/unit/test_insights_domain.py` |
| EN-09 | Bảo mật | `backend/chatdocs/adapters/http/main.py`, `infra/nginx/chatdocs.conf` | `backend/tests/api/test_security_unauthorized.py` |
| EN-10 | Bộ kiểm thử chất lượng | `eval/run_eval.py`, `eval/datasets/sample/cases.yaml` | `eval/test_run_eval.py` |
| EN-11 | Design system | `web/src/ui/primitives.tsx` | `web/src/ui/ui.test.tsx` |
| EN-12 | E2E và hiệu năng | `e2e/playwright.config.ts`, `e2e/perf/ask.js`, `backend/tests/e2e_server.py`, `e2e/fixtures/build_fixtures.py` | báo cáo Playwright / k6, `reports/test-report.md` |

## AC ↔ test case ↔ bằng chứng (L4 — Day 6)

Test case và kỳ vọng: [docs/test-cases.md](test-cases.md). Kết quả 2 lượt chạy: [reports/test-report.md](../reports/test-report.md). Ảnh chụp: `reports/screenshots/run2/<TC>.png`.

| US | AC | TC | Spec | Kết quả run1 · run2 | Bằng chứng |
|---|---|---|---|---|---|
| US-201 | AC-201.1 | TC-201-01, 02, 03, 04 | `e2e/specs/tc-us201.spec.ts` | PASS · PASS | ảnh TC-201-01…04; số đo 5,0 s tới Sẵn sàng (49,5 MB) |
| US-201 | AC-201.2 | TC-201-05, 06 | `e2e/specs/tc-us201.spec.ts` | PASS · PASS | ảnh TC-201-05-queue, 05, 06; tối đa 3 upload song song |
| US-201 | AC-201.3 | TC-201-07, 08, 09, 10, 11 | `e2e/specs/tc-us201.spec.ts` | PASS · PASS | ảnh TC-201-07…11; 0 request upload với file bị chặn ở trình duyệt |
| US-201 | AC-201.4 | TC-201-12, 13 | `e2e/specs/tc-us201.spec.ts` | PASS · PASS | ảnh TC-201-12-paused, 12, 13-failed, 13; đúng 4 lần gửi |
| US-303 | AC-303.1 | TC-303-01, 02, 03, 10 | `e2e/specs/tc-us303.spec.ts` | PASS · PASS | ảnh TC-303-01…03; `latencyMs` / `firstTokenMs` từ sự kiện `done` |
| US-303 | AC-303.2 | TC-303-04 · TC-303-05 | `e2e/specs/tc-us303.spec.ts` · thủ công | PASS · PASS · **chưa chạy** | ảnh TC-303-04-chip1, chip2 · TC-303-05 cần staging + LLM thật |
| US-303 | AC-303.3 | TC-303-06, 07, 08 | `e2e/specs/tc-us303.spec.ts` | PASS · PASS | ảnh TC-303-06…08 |
| US-303 | AC-303.4 | TC-303-09 | `e2e/specs/tc-us303.spec.ts` | PASS · PASS | trích dẫn đã lưu (annotation trong report): trang 2, excerpt là chữ PDF |

Lỗi tìm thấy khi chạy: [docs/bugs.md](bugs.md) (0 BUG sản phẩm · 4 HD · 2 TD · 1 OBS chờ PO).
