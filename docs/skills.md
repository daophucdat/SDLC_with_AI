# Danh mục skill

Skill là sản phẩm, không phải prompt: có chủ sở hữu, version, ngày xem lại và phép đo. Skill nằm ở `.claude/skills/<tên>/SKILL.md`, chia sẻ qua git. `python scripts/check_skills.py` (CI, job `traceability`) kiểm tra:

- frontmatter hợp lệ, `name` trùng tên thư mục;
- `description` + `when_to_use` ≤ 1 536 ký tự;
- SKILL.md < 500 dòng;
- có `## KHÔNG ĐƯỢC` hoặc `disallowed-tools`;
- file phụ được link có tồn tại;
- skill có một dòng trong bảng dưới;
- CLAUDE.md + AGENTS.md < 200 dòng.

## Bảng skill

| Skill | Ai gọi | Chủ sở hữu | Version | Xem lại | Mục đích · artefact | File phụ |
|---|---|---|---|---|---|---|
| `plan-tests` | **tự động** + người gọi | daophucdat | 1.0.0 | 2026-11-26 | AC → test case có kỳ vọng ghi trước → `docs/test-cases.md` | `heuristics.md`, `template.md`, `evals/triggers.json` |
| `plan-story` | tự động + người gọi | daophucdat | 1.1.0 | 2026-11-26 | Kế hoạch một story: AC → test, file theo lớp, rủi ro, ADR, câu hỏi mở (chỉ đọc) | — |
| `gen-tests` | tự động + người gọi | daophucdat | 1.1.0 | 2026-11-26 | Test tự động theo AC, đỏ trước | — |
| `review-diff` | tự động + người gọi | daophucdat | 1.1.0 | 2026-11-26 | Review L1 theo rubric, điểm /14 (chỉ đọc) | — |
| `run-test-case` | **chỉ người gọi** | daophucdat | 1.0.0 | 2026-11-26 | Chạy TC Playwright, so với kỳ vọng → `reports/tc-*.md`, phiếu `docs/bugs.md` | — |
| `commit-gate` | **chỉ người gọi** | daophucdat | 1.0.0 | 2026-11-26 | Cổng L0 trên tree đã stage → `reports/gate-<tree>.json` → commit | `scripts/gate.py` |
| `fix-ci` | **chỉ người gọi** | daophucdat | 1.1.0 | 2026-11-26 | CI đỏ → sửa nhỏ nhất theo log | — |
| `sdlc-workflow` | **chỉ người gọi** | daophucdat | 1.0.0 | 2026-11-26 | Cả vòng SDLC từ BRD, cổng duyệt mỗi pha → `docs/sdlc-state.md` | `phases.md` |

Version 1.1.0 là các lệnh `.claude/commands/*.md` của Day 5 chuyển sang dạng skill: thêm từ khoá kích hoạt, `## KHÔNG ĐƯỢC`, giới hạn công cụ. Đổi `description` thì tăng version phụ và đo lại kích hoạt; đổi quy trình thì tăng version chính.

## Vì sao chọn chế độ gọi này

Ba câu hỏi của Day 7, áp cho từng skill:

1. Có lặp lại không? Cả 8 skill đều có: mỗi story, mỗi commit, mỗi lượt test.
2. Có cần suy luận không? Có, trừ phần chạy cổng: phần đó là script `gate.py`, skill chỉ quyết định stage gì và viết message.
3. Có tác dụng phụ không?

Hai nhóm theo câu 3:

- **Có tác dụng phụ → chỉ người gọi** (`disable-model-invocation: true`):
  - `commit-gate`: tạo commit;
  - `fix-ci`: sửa code;
  - `run-test-case`: khởi động server, ghi `reports/`;
  - `sdlc-workflow`: điều phối mọi thứ.
- **Không có tác dụng phụ ngoài tài liệu / test → để Claude tự gọi.** `plan-story` và `review-diff` còn chặn hẳn `Edit` / `Write`.

Luật phải luôn đúng không nằm trong skill:

- commit có mã yêu cầu → hook `.githooks/commit-msg` + CI;
- không sửa đặc tả baseline → `permissions.deny` trong `.claude/settings.json`.

## Đo kích hoạt — `plan-tests`

Ngày đo: 2026-10-26. Lệnh: `python scripts/skill_triggers.py plan-tests`.

- Mỗi prompt chạy 1 phiên `claude -p` mới ở gốc repo, mô hình mặc định.
- Phiên chỉ đọc (cấm `Write` / `Edit` / `Bash`), tối đa 2 lượt.
- "Được gọi" = phiên gọi tool `Skill`.
- Kết quả thô: `reports/skill-triggers-plan-tests.json`.

| # | Prompt | Nên gọi | Skill được gọi | Đúng? |
|---|---|---|---|---|
| 1 | Lập test case cho US-204 gỡ tài liệu | có | plan-tests | ✅ |
| 2 | AC-303.2 test thế nào cho đủ? | có | plan-tests | ✅ |
| 3 | Story US-301 cần những kịch bản kiểm thử nào? viết giúp test plan | có | plan-tests | ✅ |
| 4 | Bổ sung TC biên và đường âm cho AC-201.1 | có | plan-tests | ✅ |
| 5 | QA sắp kiểm US-205, soạn bộ test case có kỳ vọng PASS/FAIL trước giúp tôi | có | plan-tests | ✅ |
| 6 | Viết unit test pytest cho hàm precheck trong web/src/features/library/validation.ts | không | — | ✅ |
| 7 | Review giúp diff của nhánh hiện tại so với origin/main | không | review-diff | ✅ |
| 8 | Chạy lại TC-201-05 và cho tôi ảnh chụp bằng chứng | không | — | ✅ |
| 9 | Giải thích công thức RRF trong backend/chatdocs/application/retrieval_service.py | không | — | ✅ |
| 10 | Job CI e2e-local đang đỏ, xem log và sửa giúp | không | — | ✅ |

**Kết quả:**

- Kích hoạt đúng 5/5 prompt nên gọi.
- Kích hoạt sai 0/5 prompt không nên gọi.
- Chi phí 1,48 USD.

Prompt 6–10 là "suýt trúng": cùng chủ đề test, CI hay review, nhưng thuộc skill khác. Prompt 7 được định tuyến đúng sang `review-diff`. Prompt 8 không gọi gì vì `run-test-case` chỉ người gọi — đúng thiết kế.

**Giới hạn:**

- Mỗi prompt chỉ chạy một lần, nên chưa đo được biến thiên giữa các lần chạy.
- Prompt 6 lẽ ra hợp với `gen-tests` nhưng không kích hoạt nó. Đây là điểm cần đo khi xem lại `gen-tests`.

## Có skill và không có skill — cùng một prompt

Prompt: "Lập test case cho US-204 gỡ tài liệu. Chỉ in kết quả ra đây, không ghi file." Hai phiên chạy song song:

- phiên 1 dùng skill;
- phiên 2 có `--disallowedTools Skill`.

Đầu ra đầy đủ nằm trong `reports/skill-compare/`.

| Tiêu chí ([template.md](../.claude/skills/plan-tests/template.md)) | Có skill | Không skill |
|---|---|---|
| Mọi AC có ≥ 1 TC, mọi TC trỏ về 1 AC | ✅ 22 TC / 5 AC | ✅ 19 TC / 5 AC |
| AC có giới hạn số có TC biên (**B**) hoặc âm (**N**) | ✅ có B cho AC-204.4 và AC-204.5 (hai người gỡ cùng lúc) | ✅ có B cho AC-204.4; AC-204.5 chỉ có N |
| "PASS khi" dùng chuỗi chính xác của `vi.ts`, số, mã HTTP | ✅ | ✅ |
| Tên dữ liệu riêng cho từng TC | ✅ tiền tố `G204_` | ✅ `GoBo_*` |
| TC không đến từ AC | 0 (EC-15 và việc gỡ đồng thời được gắn vào AC kèm ghi chú) | 1 (TC-204-12 "DELETE lỗi 500": tự nhận là ngoài AC) |
| Tuân thủ "không ghi file" | ✅ nói rõ ngay đầu | ✅ |
| Chi phí · lượt · thời gian | 0,53 USD · 20 lượt · 77 s | 0,68 USD · 15 lượt · 68 s |

**Đọc kết quả:** chênh lệch **nhỏ**. Repo đã có `docs/test-cases.md` làm mẫu, và CLAUDE.md / `docs/bugs.md` nêu các bài học (TD-1). Vì vậy ngay cả khi không có skill, Claude vẫn bắt chước được định dạng.

Ở repo này, skill đem lại ba điều:

1. Luôn được gọi đúng lúc (5/5).
2. Quy tắc cứng hơn: đủ biên / âm, không có TC ngoài AC, không đổi kỳ vọng.
3. Rẻ hơn một chút.

Với n = 1, đây chưa phải bằng chứng về chất lượng. Lần xem lại tới (2026-11-26) sẽ chạy mỗi phía 3 lần.
