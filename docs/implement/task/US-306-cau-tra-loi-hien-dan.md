# US-306 · Câu trả lời hiện dần

| Thuộc tính | Giá trị |
|---|---|
| Loại | User story · E3. Hỏi đáp có dẫn nguồn |
| Sprint | Sprint 3 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | P1 |
| Story point | 5 `[Đề xuất]` |
| Vai trò thực hiện | Backend, Frontend, QA |
| Phụ thuộc | US-302 |
| Chặn bởi | **TQ-01** (giữ cách "hiện dần rồi thay"?), PQ-006 (BR-009 thành Must?) |
| Feature flag | `stream_render` |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

> Là **chuyên viên BD**, tôi muốn thấy câu trả lời hiện dần trong lúc được soạn, để không phải nhìn màn hình trống khi chờ.

**Truy vết:** BR-009 · UCD-19 · NFR-02 · SAD ADR-11 (SSE)

**Thiết kế giao diện:** [`workspace.html?demo=replaced`](../../04-design/UI_UX_design/workspace.html?demo=replaced)

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** Những gì không được liệt kê ở mục 4 và mục 6.

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

**Sự kiện SSE** (dev_tasks.md §0.5)

```text
event: meta       data: {"questionId":"…","answerId":"…","readyDocCount":12,"processingDocCount":1}
event: delta      data: {"text":"Thanh toán 30% khi ký [1]"}          (0..n lần)
event: citations  data: {"text":"<câu trả lời đã đánh lại số [n]>","items":[CitationDto, …]}   (chỉ khi COMPLETED)
event: done       data: {"status":"COMPLETED|NOT_FOUND|STOPPED","reason":"NO_CHUNKS|MODEL_NOT_FOUND|INVALID_CITATIONS|null","latencyMs":8423,"firstTokenMs":2100|null}
event: error      data: {"code":"AI_TIMEOUT|AI_UNAVAILABLE|INTERNAL","retryable":true}
: ping                                                                    (comment mỗi 15 s để proxy không cắt kết nối)
```

**Quy tắc**
1. Luôn kết thúc bằng đúng **một** `done` **hoặc** `error`, sau đó đóng luồng.
2. Header phản hồi: `Content-Type: text/event-stream`, `Cache-Control: no-store`, `X-Accel-Buffering: no`.
3. Backend **giữ lại 16 ký tự đầu** của câu trả lời trước khi phát `delta`. Lý do: prompt cho phép LLM trả về token `NOT_FOUND`, và token đó không được hiện ra màn hình.
4. Nếu `done.status = NOT_FOUND` sau khi đã có `delta`, FE **thay** nội dung bằng trạng thái "không tìm thấy" (EC-14, TQ-01).

**Bảng CSDL** (trích migration `0001_init`, dev_tasks.md §0.3)

```sql
CREATE TABLE qa.answer (
  id uuid PRIMARY KEY,
  question_id uuid NOT NULL UNIQUE REFERENCES qa.question(id) ON DELETE CASCADE,
  text text NOT NULL DEFAULT '',
  status text NOT NULL CHECK (status IN ('STREAMING','COMPLETED','NOT_FOUND','STOPPED','FAILED')),
  not_found_reason text,                     -- NO_CHUNKS | MODEL_NOT_FOUND | INVALID_CITATIONS
  latency_ms int,
  first_token_ms int,
  model_id text,
  completed_at timestamptz
);
```

## 4. Công việc chi tiết

- [ ] **T306.1** `FE` — **Trạng thái AnswerCard**: Máy trạng thái theo Blueprint §3.7: `SEARCHING → STREAMING → COMPLETED / NOT_FOUND / STOPPED / FAILED / INCOMPLETE` (reducer thuần, có unit test cho mọi chuyển trạng thái)
- [ ] **T306.2** `FE` — **Hiển thị dần**: Gom `delta` theo `requestAnimationFrame` (không re-render mỗi ký tự); con trỏ nhấp nháy; vùng `aria-live` **riêng** chỉ thông báo khi bắt đầu và khi xong (không đọc từng ký tự)
- [ ] **T306.3** `FE` — **Mất kết nối**: Luồng đóng mà không có `done` / `error` → `INCOMPLETE`, giữ phần đã nhận, nút "Hỏi lại" (EC-05)
- [ ] **T306.4** `BE` — **Đo `first_token_ms`**: Lưu vào `answer.first_token_ms`; metric `qa_first_token_seconds`
- [ ] **T306.5** `QA` — **Đo NFR-02**: k6: 100 câu hỏi, 10 đồng thời → p95 phần đầu ≤ 5 s

**Chặn bởi TQ-01:** nếu quản lý quyết định không hiển thị dần, chỉ cần tắt flag `stream_render`. Khi tắt, FE giữ `delta` trong bộ nhớ và chỉ hiển thị khi nhận `done COMPLETED`; backend không đổi.

## 5. Trường hợp biên và lưu ý

- Người dùng rời trang khi đang stream → `AbortController` huỷ request; BE coi như STOPPED khi kết nối đóng.

## 6. Tiêu chí nghiệm thu

- [ ] **AC-306.1** — *Given* tôi đã gửi câu hỏi, *When* LLM bắt đầu trả lời, *Then* phần đầu tiên hiển thị trong ≤ 5 giây ở p95 (NFR-02).
- [ ] **AC-306.2** — *Given* câu trả lời đã hiện một phần, *When* kiểm tra cuối cùng thấy trích dẫn không hợp lệ, *Then* toàn bộ nội dung được thay bằng "không tìm thấy" kèm giải thích (TQ-01).
- [ ] **AC-306.3** — *Given* mất kết nối khi đang nhận, *When* luồng bị ngắt, *Then* phần đã nhận vẫn hiển thị, gắn nhãn "chưa hoàn chỉnh" và có nút "Hỏi lại" (EC-05).

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Kiểm chứng AC-306.1 như mô tả ở mục 6 | Integration | AC-306.1 |
| Kiểm chứng AC-306.2 như mô tả ở mục 6 | Integration | AC-306.2 |
| Kiểm chứng AC-306.3 như mô tả ở mục 6 | Integration | AC-306.3 |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
