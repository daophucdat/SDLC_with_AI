# EN-02 · Hạ tầng và môi trường

| Thuộc tính | Giá trị |
|---|---|
| Loại | Enabler · EN. Enabler kỹ thuật |
| Sprint | Sprint 0 ([implement_plan.md §4](../implement_plan.md)) |
| Ưu tiên | Enabler (bắt buộc cho các story phụ thuộc) |
| Story point | 8 `[Đề xuất]` — 3 điểm ở Sprint 0 (dev), 5 điểm ở Sprint 1 (staging) |
| Vai trò thực hiện | Backend, DevOps |
| Phụ thuộc | EN-01 |
| Chặn bởi | — |
| Trạng thái | To Do |
| Người nhận | `[TBD]` |

## 1. Mục tiêu

Môi trường dev / staging; PostgreSQL 16 + pgvector; object storage có mã hoá; secrets manager; OIDC client; TLS

**Truy vết:** ADR-04, ADR-06, ADR-10, ADR-12, SEC-02, SEC-03

## 2. Phạm vi

**Trong phạm vi:** các công việc ở mục 4.

**Ngoài phạm vi:** Những gì không được liệt kê ở mục 4 và mục 6.

## 3. Hợp đồng liên quan

Nguồn đầy đủ: [dev_tasks.md — Phần 0](../dev_tasks.md). Đổi hợp đồng thì sửa ở đó trước.

**Bảng CSDL** (trích migration `0001_init`, dev_tasks.md §0.3)

```sql
CREATE UNIQUE INDEX ux_user_email ON access.app_user (lower(email));

CREATE TABLE access.session (
  id_hash bytea PRIMARY KEY,                -- sha256(cookie value)
  user_id uuid NOT NULL REFERENCES access.app_user(id),
  csrf_secret bytea NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  last_activity_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX ix_session_activity ON access.session (last_activity_at);

CREATE INDEX ix_doc_status ON documents.document (library_id, status);

CREATE INDEX ix_doc_name_trgm ON documents.document USING gin (file_name gin_trgm_ops);

CREATE TABLE documents.document_page (
  document_id uuid REFERENCES documents.document(id) ON DELETE CASCADE,
  page_number int NOT NULL,
  text text NOT NULL,
  PRIMARY KEY (document_id, page_number)
);

CREATE TABLE documents.text_chunk (
  id uuid PRIMARY KEY,
  document_id uuid NOT NULL REFERENCES documents.document(id) ON DELETE CASCADE,
  page_number int NOT NULL,
  chunk_index int NOT NULL,
  char_start int NOT NULL,
  char_end int NOT NULL,
  content text NOT NULL,
  tsv tsvector GENERATED ALWAYS AS (to_tsvector('simple', platform.f_unaccent(content))) STORED,
  embedding vector(1024) NOT NULL
);

CREATE INDEX ix_chunk_doc ON documents.text_chunk (document_id);

CREATE INDEX ix_chunk_tsv ON documents.text_chunk USING gin (tsv);

CREATE INDEX ix_chunk_vec ON documents.text_chunk USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

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

CREATE TABLE qa.citation (
  answer_id uuid REFERENCES qa.answer(id) ON DELETE CASCADE,
  idx int NOT NULL,
  chunk_id uuid REFERENCES documents.text_chunk(id) ON DELETE SET NULL,    -- EC-15
  document_id uuid NOT NULL,
  file_name text NOT NULL,
  page_number int NOT NULL,
  excerpt text NOT NULL,
  PRIMARY KEY (answer_id, idx)
);

CREATE TABLE qa.feedback (
  answer_id uuid PRIMARY KEY REFERENCES qa.answer(id) ON DELETE CASCADE,
  value text NOT NULL CHECK (value IN ('HELPFUL','NOT_HELPFUL')),
  reason text CHECK (reason IN ('wrong','incomplete','wrong_source','other')),
  submitted_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX ix_event_name_ts ON analytics.event (name, ts);

CREATE TABLE analytics.daily_rollup (day date, metric text, value numeric NOT NULL, PRIMARY KEY (day, metric));

CREATE INDEX ix_job_ready ON platform.job (run_after) WHERE status = 'queued';

CREATE TABLE platform.audit_log (
  id bigint GENERATED ALWAYS AS IDENTITY,
  ts timestamptz NOT NULL DEFAULT now(),
  actor_id uuid, action text NOT NULL, target_type text, target_id text, ip inet,
  PRIMARY KEY (id, ts)
) PARTITION BY RANGE (ts);
```

## 4. Công việc chi tiết

- [ ] **T-EN02.1** `INF` — **`infra/docker-compose.yml`**: Dịch vụ `postgres` (pgvector/pg16), `minio`, `embedder`, `api`, `worker`, `web` (Vite dev), `keycloak` (IdP thử, realm có 3 nhóm và 4 user mẫu)
- [ ] **T-EN02.2** `DB` — **Migration `0001_init`**: DDL §0.3 + seed library; `alembic upgrade head` chạy khi `api` khởi động (môi trường dev)
- [ ] **T-EN02.3** `INF` — **Staging (Sprint 1)**: Theo ADR-12 (đám mây hoặc nội bộ, chờ OQ-008): 2 bản sao `api`, 1 `worker`, 1 `embedder`; PostgreSQL có standby; bucket có SSE và chặn truy cập công khai; LB có TLS 1.3, giới hạn body 55 MB, `proxy_buffering off`, `proxy_read_timeout 60s` cho `/api/v1/conversations/*/questions`
- [ ] **T-EN02.4** `INF` — **Secrets**: Secrets manager / Vault; không có secret trong repo (thêm `gitleaks` vào CI)
- [ ] **T-EN02.5** `INF` — **Deploy tự động**: Merge vào `main` → build image → deploy staging → chạy migration → smoke test `/readyz`

## 5. Trường hợp biên và lưu ý

- Xem các trường hợp lỗi ở mục 3 (mã lỗi) và các tiêu chí nghiệm thu ở mục 6.

## 6. Tiêu chí nghiệm thu

- [ ] `docker compose up` chạy được ở máy dev; staging truy cập được qua HTTPS; secrets không nằm trong repo

## 7. Kiểm thử

| Test | Loại | Ánh xạ |
|---|---|---|
| Kiểm chứng tiêu chí hoàn thành ở mục 6 | Integration / báo cáo | EN-02 |

## 8. Definition of Done

- [ ] Mọi tiêu chí nghiệm thu ở mục 6 đạt, có test tự động chạy trong CI.
- [ ] Code đã được review; CI xanh (lint, quy tắc import DR-1 → DR-5, unit, integration).
- [ ] Không ghi nội dung câu hỏi / câu trả lời / tài liệu vào log, span hay sự kiện (QAS-06).
- [ ] Mọi tham số lấy từ cấu hình (§0.2 của dev_tasks.md), không hard-code.
- [ ] Nếu có giao diện: đúng prototype, dùng design token, axe không có lỗi serious / critical.
- [ ] Đã deploy lên staging và PO / BA nghiệm thu bằng demo.

---

*Sinh từ [userStory.md](../userStory.md) và [dev_tasks.md](../dev_tasks.md). Khi hai tài liệu nguồn thay đổi, cập nhật file này cho khớp.*
