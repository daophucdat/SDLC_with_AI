# US-310 · Dừng câu trả lời đang soạn

| Thuộc tính | Giá trị |
|---|---|
| Loại | User story · E3. Hỏi đáp có dẫn nguồn |
| Sprint | Sprint 3 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | P1 |
| Story point | 3 `[Đề xuất]` |
| Vai trò thực hiện | Backend, Frontend |
| Phụ thuộc | US-306 |
| Chặn bởi | — |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

> Là **chuyên viên BD**, tôi muốn dừng một câu trả lời đang soạn, để hỏi lại ngay khi nhận ra mình hỏi sai.

**Truy vết:** BR-009 · UCD-23 · SAD §3.2.1 bước 9

**Thiết kế giao diện:** [`workspace.html?demo=stopped`](../../04-design/UI_UX_design/workspace.html?demo=stopped)

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** Những gì không được liệt kê ở mục 4 và mục 6.

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

**API**

| # | Endpoint | Request | Response 2xx | Lỗi (code) | Story |
|---|---|---|---|---|---|
| Q4 | `POST /api/v1/answers/{id}/stop` | — | 202 | 404 · 409 INVALID_STATE | US-310 |

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

**Mã lỗi**

| code | HTTP | Thông điệp FE (`vi.ts`) | Hành động FE |
|---|---|---|---|
| INVALID_STATE | 409 | — | Làm mới dữ liệu |

**Sự kiện phân tích** (danh sách cho phép, không có trường nội dung)

| name | Nguồn | props cho phép |
|---|---|---|
| `answer_stopped` | BE | `elapsed_ms: int` |

## 4. Công việc chi tiết

- [ ] **T310.1** `BE` — **`POST /answers/{id}/stop`**: Kiểm tra chủ sở hữu và `status=STREAMING`; đặt cờ `stop_flags[answer_id].set()` nếu luồng chạy ở bản sao này; nếu không thì `NOTIFY answer_stop, '<id>'` để bản sao đang chạy luồng tự đặt cờ
- [ ] **T310.2** `BE` — **Xử lý khi dừng**: Vòng lặp stream thấy cờ → huỷ lời gọi LLM (thoát `async for`, đóng response) → `status=STOPPED`, lưu phần đã có → `done STOPPED`; sự kiện `answer_stopped {elapsed_ms}`
- [ ] **T310.3** `FE` — **Nút Dừng**: Khi đang `STREAMING`, nút Gửi thành "⏹ Dừng" (`aria-label` "Dừng câu trả lời đang soạn"); bấm → gọi Q4, ngừng nhận `delta` ngay (≤ 1 s), focus về ô câu hỏi

## 5. Trường hợp biên và lưu ý

- Bấm Dừng sau khi đã có `done` → API trả 409, FE bỏ qua.

## 6. Tiêu chí nghiệm thu

- [ ] **AC-310.1** — *Given* câu trả lời đang hiện dần, *When* tôi bấm "Dừng", *Then* câu trả lời ngừng trong ≤ 1 giây, gắn nhãn "Đã dừng", ô câu hỏi dùng được ngay.
- [ ] **AC-310.2** — *Given* tôi đã bấm Dừng, *When* kiểm tra phía máy chủ, *Then* lời gọi LLM đã bị huỷ (không tốn thêm token) và sinh sự kiện `answer_stopped`.

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Kiểm chứng AC-310.1 như mô tả ở mục 6 | Integration | AC-310.1 |
| Kiểm chứng AC-310.2 như mô tả ở mục 6 | Integration | AC-310.2 |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
