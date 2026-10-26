# Test plan — Chat với tài liệu (MVP) · 2 user story xương sống

| Thuộc tính | Giá trị |
|---|---|
| Phiên bản | 1.0 · 2026-10-26 |
| Chuẩn tham chiếu | ISO/IEC/IEEE 29119-3 (tài liệu kiểm thử, bản diễn giải), ISO/IEC 25010 |
| Người lập / phê duyệt | QA (lập) · Tech lead + Trưởng nhóm BD (phê duyệt báo cáo) |
| Test case | [docs/test-cases.md](test-cases.md) · Báo cáo: [reports/test-report.md](../reports/test-report.md) |

## 1. Mục tiêu
Chứng minh bằng bằng chứng chạy thật trên trình duyệt rằng 2 user story xương sống đạt các AC **đã baseline** trong `docs/implement/userStory.md`:
**US-201** Tải một hoặc nhiều file PDF (AC-201.1 → 201.4) và **US-303** Mỗi ý có trích dẫn tài liệu và trang (AC-303.1 → 303.4). Day 5 đã có L0 (CI xanh); test plan này thêm lớp **L4 — verification**: test case lấy từ AC, PASS/FAIL định nghĩa trước khi chạy.

## 2. Phạm vi
- **UI + API trên trình duyệt** (Chromium headless qua Playwright): màn hình làm việc, kho tài liệu, ô câu hỏi, thẻ câu trả lời, vùng nguồn.
- **API** trực tiếp khi AC nói về dữ liệu lưu (AC-303.4) hoặc chỉ số đo (độ trễ).
- Luồng đăng nhập chỉ là tiền điều kiện (US-101 có bộ test riêng).

## 3. Non-goals (không kiểm thử trong đợt này)
- Các story khác (gỡ tài liệu, số liệu, nghiệm thu, …) — đã có test tự động ở L0, không thuộc đợt L4 này.
- Chất lượng câu trả lời của **LLM thật** (KR2.1, LG-03) — đo bằng harness `eval/` trên staging.
- Tải nhiều người dùng đồng thời / k6 (LG-06), tối ưu chi phí AI, đa trình duyệt (Edge — LG-14), đa ngôn ngữ ngoài vi/en.
- Keycloak, PostgreSQL, MinIO, TEI thật — có ở job CI `e2e` (docker compose); đợt này dùng môi trường test cục bộ (mục 5).

## 4. Chiến lược (phân lớp, ai thực thi)
| Lớp | Nội dung | Thực thi | Khi nào |
|---|---|---|---|
| L0 | lint, type, unit/API/integration test, coverage, audit, traceability | CI (Day 5) | mọi commit |
| **L4** | **22 test case tự động** của `docs/test-cases.md` (TC-201-01 → 13, TC-303-01 → 10 trừ TC-303-05), mỗi TC một test Playwright mang mã TC | Claude Code chạy Playwright (`npm run test:tc`); người chốt kết luận khó | mỗi PR (job CI `e2e-local`) + trước demo |
| L4 thủ công | TC-303-05 (mẫu 30 trích dẫn, LG-05) | QA + Trưởng nhóm BD trên staging, LLM thật | trước Go / No-go |

Thứ tự: **plan → test case (PASS/FAIL ghi trước) → thực thi → báo cáo**. Không chạy trước khi có định nghĩa PASS. TC FAIL → bug ticket → sửa code ở phiên riêng → chạy lại TC; **không sửa test cho pass**.

## 5. Môi trường & dữ liệu
| Mục | Giá trị |
|---|---|
| App test | SPA `http://localhost:5180` (Vite, cổng riêng `E2E_WEB_PORT`, không dùng lại server đang chạy — xem HD-3) → API `http://localhost:8000` (`E2E_API_PORT`) = `backend/tests/e2e_server.py`: app FastAPI thật, xử lý PDF thật (PyMuPDF), kho / chỉ mục / CSDL **trong bộ nhớ**, LLM **giả lập có kịch bản** (`#noref`, `#badref` để tạo câu trả lời sai trích dẫn), IdP thử. Mỗi lần chạy khởi động server mới → dữ liệu sạch, lặp lại được |
| Tài khoản | `member` (Trần Thu Hà, Thành viên BD) qua trang IdP thử |
| Cấu hình đặc thù | giới hạn upload thật 50 MB; giới hạn tần suất nâng lên (500 upload/giờ) để chạy lại nhiều lần — bản thân giới hạn có test API riêng |
| Dữ liệu (sinh bởi `e2e/fixtures/build_fixtures.py`, không commit) | `HopDong_ABC.pdf` (3 trang tiếng Việt: phạm vi / **thanh toán trang 2** / bảo hành trang 3) · `BaoGia_XYZ.pdf` (2 trang) · tên file tiếng Việt có dấu · PDF hợp lệ **49,5 MB** và 2 PDF 8 MB · 19 PDF nhỏ khác nội dung · file **50 MB + 1 KB** · `.doc` đổi đuôi `.pdf` · PDF 0 byte · ảnh `.png` · PDF hỏng |
| Trình duyệt | Chromium (Playwright 1.40) headless, 1440×900, `vi-VN`; mạng chậm giả lập bằng CDP khi cần thấy % tiến độ |

## 6. Rủi ro & ưu tiên (test trước cái dễ vỡ nhất)
| # | Rủi ro | Ưu tiên | TC |
|---|---|---|---|
| R1 | Trích dẫn sai trang / bịa nguồn → người dùng mất niềm tin (BR-007) | Cao | TC-303-01, 04, 06, 07, 09 |
| R2 | File lớn sát 50 MB: tải chậm, không thấy tiến độ, quá NFR-03 | Cao | TC-201-03, 04, 08 |
| R3 | Mất mạng giữa chừng → file kẹt hoặc mất | Cao | TC-201-12, 13 |
| R4 | File không hợp lệ lọt vào kho / làm hỏng lô | Trung bình | TC-201-06, 07, 09, 10, 11 |
| R5 | Prompt injection trong tài liệu | Trung bình — ngoài 2 story; có ca `S08` ở `eval/` và T-EN09.7 | — |

## 7. Tiêu chí thoát
- **100% AC** của US-201 và US-303 có ≥ 1 TC; **không TC nào** không trỏ về AC (ma trận ở cuối `test-cases.md`).
- 100% TC tự động **PASS**, hoặc FAIL có bug ticket trong `docs/bugs.md`; TC chưa chạy được phải ghi lý do và người chịu trách nhiệm.
- PASS **lặp lại được**: chạy toàn bộ ≥ 2 lần liên tiếp, kết quả không đổi (không có TC "flaky").
- Mỗi TC để lại bằng chứng: screenshot + trace (Playwright) + dòng kết quả trong `reports/test-report.md`.

## 8. Artifacts trong repo
| Artifact | Đường dẫn |
|---|---|
| Test plan | `docs/test-plan.md` (file này) |
| Test case + ma trận AC ↔ TC | `docs/test-cases.md` |
| Spec Playwright (mỗi test mang mã TC) | `e2e/specs/tc-us201.spec.ts`, `e2e/specs/tc-us303.spec.ts` |
| Bằng chứng chạy | `reports/test-report.md` (tổng hợp, 2 lần chạy), `reports/junit-run*.xml`, `reports/screenshots/<run>/<TC>.png`; bảng kết quả sinh bằng `python scripts/test_report.py`; trace + HTML report trong `e2e/playwright-report/` và artifact CI |
| Bug | `docs/bugs.md` (một dòng mỗi TC FAIL) |
| Truy vết | `docs/traceability.md` — US ↔ AC ↔ TC ↔ bằng chứng |
