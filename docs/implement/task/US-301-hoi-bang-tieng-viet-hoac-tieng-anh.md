# US-301 · Hỏi bằng tiếng Việt hoặc tiếng Anh

| Thuộc tính | Giá trị |
|---|---|
| Loại | User story · E3. Hỏi đáp có dẫn nguồn |
| Sprint | Sprint 2 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | P0 |
| Story point | 3 `[Đề xuất]` |
| Vai trò thực hiện | Backend, Frontend |
| Phụ thuộc | EN-11 (QuestionComposer) |
| Chặn bởi | OQ-014 (ngôn ngữ) — tạm tiếng Việt + tiếng Anh |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

> Là **chuyên viên BD**, tôi muốn gõ câu hỏi bằng tiếng Việt hoặc tiếng Anh như khi hỏi đồng nghiệp, để không phải học cú pháp tìm kiếm.

**Truy vết:** BR-002 · UCD-16 · AC-002

**Thiết kế giao diện:** [`workspace.html?scenario=empty`](../../04-design/UI_UX_design/workspace.html?scenario=empty)

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** Những gì không được liệt kê ở mục 4 và mục 6.

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

**API**

| # | Endpoint | Request | Response 2xx | Lỗi (code) | Story |
|---|---|---|---|---|---|
| Q1 | `POST /api/v1/conversations` | — | 201 `{id}` | — | US-301 |
| Q2 | `POST /api/v1/conversations/{id}/questions` | `{text, followUp?: bool}` | 200 `text/event-stream` (§0.5) | 400 QUESTION_INVALID · 409 NO_READY_DOCUMENTS · 429 RATE_LIMITED · 503 AI_BUSY | US-301 → 306, 311 |

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
CREATE TABLE qa.question (
  id uuid PRIMARY KEY,
  conversation_id uuid NOT NULL REFERENCES qa.conversation(id) ON DELETE CASCADE,
  text text NOT NULL CHECK (char_length(text) BETWEEN 1 AND 2000),
  language text NOT NULL CHECK (language IN ('vi','en')),
  is_followup boolean NOT NULL DEFAULT false,
  asked_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX ix_question_conv ON qa.question (conversation_id, asked_at);

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
| RATE_LIMITED | 429 | "Bạn thao tác quá nhanh, thử lại sau {retryAfter} giây." | Toast |
| QUESTION_INVALID | 400 | — | (FE đã chặn trước) |
| NO_READY_DOCUMENTS | 409 | "Chưa có tài liệu sẵn sàng." | Vô hiệu ô câu hỏi |

**Sự kiện phân tích** (danh sách cho phép, không có trường nội dung)

| name | Nguồn | props cho phép |
|---|---|---|
| `question_submitted` | BE | `language`, `question_length: int`, `ready_doc_count: int`, `is_suggested: bool`, `turn_index: int` |

## 4. Công việc chi tiết

- [ ] **T301.1** `BE` — **`Question.create`**: Kiểm `1 ≤ len(strip) ≤ 2000`; nhận diện ngôn ngữ: có ký tự tiếng Việt có dấu (regex `[à-ỹđ]`, không phân biệt hoa thường) → `vi`, ngược lại `en`
- [ ] **T301.2** `BE` — **`POST /conversations`, `POST …/questions`**: Router trả `StreamingResponse(media_type="text/event-stream")`; mỗi sự kiện `event: X\ndata: <json>\n\n`; task phụ phát `: ping` mỗi 15 s; giới hạn tần suất `RATE_QUESTIONS_PER_MIN`
- [ ] **T301.3** `FE` — **`QuestionComposer`**: Textarea tự giãn (tối đa 160 px); Enter gửi, Shift+Enter xuống dòng, bỏ qua khi `isComposing` (bộ gõ tiếng Việt); bộ đếm `n/2000` (cảnh báo > 1.800, khoá > 2.000); bị vô hiệu kèm lý do khi không có tài liệu READY / mất mạng / AI gián đoạn; bản nháp lưu `sessionStorage`
- [ ] **T301.4** `FE` — **`sse.ts` + `useAsk`**: `fetch(POST)` + `ReadableStream` + `TextDecoder`; tách sự kiện theo `\n\n`; bỏ qua dòng bắt đầu bằng `:`; `AbortController` để huỷ khi rời trang; chuyển trạng thái theo §0.5 vào `useChatStore`
- [ ] **T301.5** `FE` — **`ChatThread` + trạng thái rỗng**: Kho rỗng → vùng kéo-thả lớn (EC-01); chưa có câu hỏi → 3 câu hỏi mẫu (EC-02); câu hỏi gửi từ gợi ý có `is_suggested=true`

**Luồng xử lý chung của US-301 → US-304** (`application/qa/question_answering_service.py`). Story này hiện thực phần được đánh dấu bằng mã story trong comment; các phần còn lại thuộc story khác cùng sprint.

```python
async def ask(user, conversation_id, text, follow_up) -> AsyncIterator[SseEvent]:
    t0 = monotonic()
    q = Question.create(conversation_id, text)                  # domain kiểm 1..2000 ký tự, nhận diện vi/en
    docs = await library.ready_documents()                      # US-202 AC-202.2
    if not docs: raise NoReadyDocuments()                       # 409, trước khi mở luồng
    processing_count = await library.processing_count()
    answer = Answer.start(q.id)
    await repo.save_question_and_answer(q, answer)              # cùng 1 giao dịch
    yield Meta(q.id, answer.id, len(docs), processing_count)
    analytics.track("question_submitted", ...)                  # fire-and-forget

    query = build_query(text, history if follow_up else None)   # US-311
    vec = await embedder.embed_query(query)
    found = await chunk_index.search(query, vec, [d.id for d in docs])
    if found.is_empty(tau):                                     # ALG-2 → US-304
        for ev in await finish_not_found(answer, "NO_CHUNKS", t0):   # async generator: không dùng `yield from`
            yield ev
        return

    prompt = PromptBuilder.v1(found.chunks, text, q.language, history)
    buf, released, first_token_ms = "", False, None
    async with breaker, semaphore:
        async for piece in llm.stream(prompt, cancel=stop_flags[answer.id]):
            first_token_ms = first_token_ms or ms_since(t0)
            buf += piece
            if not released and (len(buf) >= 16 and not "NOT_FOUND".startswith(buf.strip()[:9])):
                released = True; yield Delta(buf)               # giữ 16 ký tự đầu (§0.5)
            elif released:
                yield Delta(piece)

    result = CitationPolicy.validate(buf, found.chunks)        # ALG-3 → US-303
    if result.not_found:
        for ev in await finish_not_found(answer, result.reason, t0):
            yield ev
        return
    await repo.complete(answer, result.text, result.citations, latency=ms_since(t0), first_token_ms=first_token_ms)
    yield Citations(result.citations, text=result.text)        # text đã đánh lại số [n] (DQ-01)
    yield Done("COMPLETED", ms_since(t0))
```

`finish_not_found(answer, reason, t0) -> list[SseEvent]`: cập nhật `answer` (NOT_FOUND, reason, latency), ghi sự kiện `answer_completed(is_not_found=true)`, trả `[Done("NOT_FOUND", reason, latency)]`. Nếu câu trả lời ngắn hơn 16 ký tự, sẽ không có `delta` nào được phát; FE vẫn hiển thị nhờ trường `text` của sự kiện `citations`.

Ngoại lệ: `GenerationTimeout` → `answer.status=FAILED`, phát `error AI_TIMEOUT`. `CircuitOpen` / `GenerationUnavailable` → `error AI_UNAVAILABLE`. Cả hai đều ghi sự kiện `answer_failed`.

## 5. Trường hợp biên và lưu ý

- Xem các trường hợp lỗi ở mục 3 (mã lỗi) và các tiêu chí nghiệm thu ở mục 6.

## 6. Tiêu chí nghiệm thu

- [ ] **AC-301.1** — *Given* kho có ≥ 1 tài liệu "Sẵn sàng", *When* tôi gõ câu hỏi tiếng Việt và nhấn Enter, *Then* câu hỏi được gửi và câu trả lời bằng tiếng Việt bắt đầu hiện.
- [ ] **AC-301.2** — *Given* như trên, *When* tôi hỏi bằng tiếng Anh, *Then* câu trả lời bằng tiếng Anh.
- [ ] **AC-301.3** — *Given* ô câu hỏi trống hoặc chỉ có khoảng trắng, *When* tôi nhấn Enter, *Then* không có gì được gửi.
- [ ] **AC-301.4** — *Given* câu hỏi > 2.000 ký tự, *When* tôi gõ tiếp, *Then* bộ đếm chuyển màu cảnh báo và nút Gửi bị vô hiệu.
- [ ] **AC-301.5** — *Given* kho chưa có tài liệu "Sẵn sàng", *When* tôi mở màn hình, *Then* ô câu hỏi bị vô hiệu kèm lý do (EC-01, EC-03).

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Câu tiếng Việt → trả lời tiếng Việt; câu tiếng Anh → tiếng Anh | E2E (fake LLM theo ngôn ngữ) + đánh giá | AC-301.1, 301.2 |
| Ô trống / chỉ khoảng trắng / > 2.000 ký tự | Unit FE + BE | AC-301.3, 301.4 |
| Kho không có READY → ô bị vô hiệu; gọi API → 409 | E2E + integration | AC-301.5 |
| Token `NOT_FOUND` không bao giờ xuất hiện trong `delta` | Unit (luồng giả) | §0.5 |
| Contract: mọi luồng kết thúc bằng đúng 1 `done` hoặc `error` | Contract | §0.5 |
| Kiểm chứng AC-301.2 như mô tả ở mục 6 | E2E | AC-301.2 |
| Kiểm chứng AC-301.4 như mô tả ở mục 6 | E2E | AC-301.4 |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
