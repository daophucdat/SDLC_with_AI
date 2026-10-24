"""Initial schema (dev_tasks.md §0.3, SAD §3.1).

Generated from the SQL block in docs/implement/dev_tasks.md so both stay identical. Two additions:
- DEFAULT partitions for the partitioned tables: without one, the first INSERT (login audit) fails.
  The monthly partition job (EN-08) attaches real partitions later.
- The shared library row (PD-01); its id is chatdocs.platform.config.DEFAULT_LIBRARY_ID.

Revision ID: 0001
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

STATEMENTS = [
    "CREATE EXTENSION IF NOT EXISTS vector",
    "CREATE EXTENSION IF NOT EXISTS unaccent",
    "CREATE EXTENSION IF NOT EXISTS pg_trgm",
    "CREATE SCHEMA access",
    "CREATE SCHEMA documents",
    "CREATE SCHEMA qa",
    "CREATE SCHEMA analytics",
    "CREATE SCHEMA platform",
    "CREATE SCHEMA evaluation",
    "CREATE FUNCTION platform.f_unaccent(text) RETURNS text\n  LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT\n  AS $$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $$",
    "CREATE TABLE access.app_user (\n  id uuid PRIMARY KEY,\n  email text NOT NULL,\n  display_name text NOT NULL,\n  role text NOT NULL CHECK (role IN ('BD_MEMBER','BD_LEAD','MANAGER')),\n  active boolean NOT NULL DEFAULT true,\n  created_at timestamptz NOT NULL DEFAULT now(),\n  last_login_at timestamptz\n)",
    "CREATE UNIQUE INDEX ux_user_email ON access.app_user (lower(email))",
    "CREATE TABLE access.session (\n  id_hash bytea PRIMARY KEY,                -- sha256(cookie value)\n  user_id uuid NOT NULL REFERENCES access.app_user(id),\n  csrf_secret bytea NOT NULL,\n  created_at timestamptz NOT NULL DEFAULT now(),\n  last_activity_at timestamptz NOT NULL DEFAULT now()\n)",
    "CREATE INDEX ix_session_activity ON access.session (last_activity_at)",
    "CREATE TABLE documents.library (id uuid PRIMARY KEY, name text NOT NULL)",
    "CREATE TABLE documents.document (\n  id uuid PRIMARY KEY,\n  library_id uuid NOT NULL REFERENCES documents.library(id),\n  file_name text NOT NULL,\n  size_bytes bigint NOT NULL CHECK (size_bytes > 0 AND size_bytes <= 52428800),\n  page_count int,\n  content_hash bytea NOT NULL,              -- sha256 nội dung file\n  status text NOT NULL CHECK (status IN ('UPLOADING','PROCESSING','READY','NO_TEXT','ERROR','REMOVED')),\n  error_code text,                          -- PASSWORD | CORRUPT | NOT_PDF | TIMEOUT | INTERNAL\n  storage_key text NOT NULL,\n  uploaded_by uuid NOT NULL REFERENCES access.app_user(id),\n  uploaded_at timestamptz NOT NULL DEFAULT now(),\n  removed_at timestamptz,\n  removed_by uuid REFERENCES access.app_user(id),\n  purged_at timestamptz\n)",
    "CREATE INDEX ix_doc_hash ON documents.document (library_id, content_hash) WHERE removed_at IS NULL",
    "CREATE INDEX ix_doc_status ON documents.document (library_id, status)",
    "CREATE INDEX ix_doc_name_trgm ON documents.document USING gin (file_name gin_trgm_ops)",
    "CREATE TABLE documents.document_page (\n  document_id uuid REFERENCES documents.document(id) ON DELETE CASCADE,\n  page_number int NOT NULL,\n  text text NOT NULL,\n  PRIMARY KEY (document_id, page_number)\n)",
    "CREATE TABLE documents.text_chunk (\n  id uuid PRIMARY KEY,\n  document_id uuid NOT NULL REFERENCES documents.document(id) ON DELETE CASCADE,\n  page_number int NOT NULL,\n  chunk_index int NOT NULL,\n  char_start int NOT NULL,\n  char_end int NOT NULL,\n  content text NOT NULL,\n  tsv tsvector GENERATED ALWAYS AS (to_tsvector('simple', platform.f_unaccent(content))) STORED,\n  embedding vector(1024) NOT NULL\n)",
    "CREATE INDEX ix_chunk_doc ON documents.text_chunk (document_id)",
    "CREATE INDEX ix_chunk_tsv ON documents.text_chunk USING gin (tsv)",
    "CREATE INDEX ix_chunk_vec ON documents.text_chunk USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)",
    "CREATE TABLE qa.conversation (\n  id uuid PRIMARY KEY,\n  session_id bytea NOT NULL REFERENCES access.session(id_hash) ON DELETE CASCADE,   -- PD-04\n  user_id uuid NOT NULL REFERENCES access.app_user(id),\n  started_at timestamptz NOT NULL DEFAULT now()\n)",
    "CREATE TABLE qa.question (\n  id uuid PRIMARY KEY,\n  conversation_id uuid NOT NULL REFERENCES qa.conversation(id) ON DELETE CASCADE,\n  text text NOT NULL CHECK (char_length(text) BETWEEN 1 AND 2000),\n  language text NOT NULL CHECK (language IN ('vi','en')),\n  is_followup boolean NOT NULL DEFAULT false,\n  asked_at timestamptz NOT NULL DEFAULT now()\n)",
    "CREATE INDEX ix_question_conv ON qa.question (conversation_id, asked_at)",
    "CREATE TABLE qa.answer (\n  id uuid PRIMARY KEY,\n  question_id uuid NOT NULL UNIQUE REFERENCES qa.question(id) ON DELETE CASCADE,\n  text text NOT NULL DEFAULT '',\n  status text NOT NULL CHECK (status IN ('STREAMING','COMPLETED','NOT_FOUND','STOPPED','FAILED')),\n  not_found_reason text,                     -- NO_CHUNKS | MODEL_NOT_FOUND | INVALID_CITATIONS\n  latency_ms int,\n  first_token_ms int,\n  model_id text,\n  completed_at timestamptz\n)",
    "CREATE TABLE qa.citation (\n  answer_id uuid REFERENCES qa.answer(id) ON DELETE CASCADE,\n  idx int NOT NULL,\n  chunk_id uuid REFERENCES documents.text_chunk(id) ON DELETE SET NULL,    -- EC-15\n  document_id uuid NOT NULL,\n  file_name text NOT NULL,\n  page_number int NOT NULL,\n  excerpt text NOT NULL,\n  PRIMARY KEY (answer_id, idx)\n)",
    "CREATE TABLE qa.feedback (\n  answer_id uuid PRIMARY KEY REFERENCES qa.answer(id) ON DELETE CASCADE,\n  value text NOT NULL CHECK (value IN ('HELPFUL','NOT_HELPFUL')),\n  reason text CHECK (reason IN ('wrong','incomplete','wrong_source','other')),\n  submitted_at timestamptz NOT NULL DEFAULT now()\n)",
    "CREATE TABLE analytics.event (\n  id bigint GENERATED ALWAYS AS IDENTITY,\n  name text NOT NULL,\n  ts timestamptz NOT NULL DEFAULT now(),\n  user_id_hash text NOT NULL,\n  session_id text,\n  app_version text NOT NULL,\n  props jsonb NOT NULL DEFAULT '{}',\n  PRIMARY KEY (id, ts)\n) PARTITION BY RANGE (ts)",
    "CREATE INDEX ix_event_name_ts ON analytics.event (name, ts)",
    "CREATE TABLE analytics.daily_rollup (day date, metric text, value numeric NOT NULL, PRIMARY KEY (day, metric))",
    "CREATE TABLE platform.job (\n  id uuid PRIMARY KEY,\n  type text NOT NULL CHECK (type IN ('process_document','purge_document','run_evaluation','sweep_sessions','rollup_metrics')),\n  payload jsonb NOT NULL,\n  status text NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','done','failed')),\n  attempts int NOT NULL DEFAULT 0,\n  run_after timestamptz NOT NULL DEFAULT now(),\n  locked_by text, locked_at timestamptz, last_error text,\n  created_at timestamptz NOT NULL DEFAULT now()\n)",
    "CREATE INDEX ix_job_ready ON platform.job (run_after) WHERE status = 'queued'",
    "CREATE TABLE platform.audit_log (\n  id bigint GENERATED ALWAYS AS IDENTITY,\n  ts timestamptz NOT NULL DEFAULT now(),\n  actor_id uuid, action text NOT NULL, target_type text, target_id text, ip inet,\n  PRIMARY KEY (id, ts)\n) PARTITION BY RANGE (ts)",
    "CREATE TABLE evaluation.test_set (id uuid PRIMARY KEY, name text NOT NULL, created_by uuid, created_at timestamptz DEFAULT now())",
    "CREATE TABLE evaluation.test_case (\n  id uuid PRIMARY KEY, test_set_id uuid REFERENCES evaluation.test_set(id) ON DELETE CASCADE,\n  ordinal int NOT NULL, question text NOT NULL, expected_answer text, expects_not_found boolean NOT NULL DEFAULT false\n)",
    "CREATE TABLE evaluation.run (\n  id uuid PRIMARY KEY, test_set_id uuid REFERENCES evaluation.test_set(id),\n  status text NOT NULL, started_at timestamptz, finished_at timestamptz, done_count int DEFAULT 0, total int NOT NULL\n)",
    "CREATE TABLE evaluation.result (\n  run_id uuid REFERENCES evaluation.run(id) ON DELETE CASCADE, test_case_id uuid REFERENCES evaluation.test_case(id),\n  answer_text text, status text, citations jsonb, latency_ms int, PRIMARY KEY (run_id, test_case_id)\n)",
    "CREATE TABLE analytics.event_default PARTITION OF analytics.event DEFAULT",
    "CREATE TABLE platform.audit_log_default PARTITION OF platform.audit_log DEFAULT",
    "INSERT INTO documents.library (id, name) VALUES ('01920000-0000-7000-8000-000000000001', 'Kho tài liệu đội BD')",
]


def upgrade() -> None:
    # One statement per execute(): asyncpg prepared statements cannot hold several commands.
    for statement in STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for schema in ("evaluation", "platform", "analytics", "qa", "documents", "access"):
        op.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
