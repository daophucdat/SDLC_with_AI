-- REL-02 step 1 / step 5: snapshot of the library to compare before and after a restore.
-- psql "$DATABASE_URL" -f infra/backup/capture_state.sql > state-<when>.txt
SELECT now() AS captured_at;
SELECT status, count(*) AS documents FROM documents.document GROUP BY status ORDER BY status;
SELECT count(*) AS chunks, count(DISTINCT document_id) AS documents_with_chunks FROM documents.text_chunk;
SELECT count(*) AS pages FROM documents.document_page;
SELECT count(*) AS users, count(*) FILTER (WHERE active) AS active_users FROM access.app_user;
SELECT count(*) AS purge_pending FROM documents.document WHERE removed_at IS NOT NULL AND purged_at IS NULL;
-- fingerprint of the indexed content (changes if any chunk is missing or different)
SELECT md5(string_agg(id::text || ':' || md5(content), ',' ORDER BY id)) AS chunk_fingerprint FROM documents.text_chunk;
SELECT version_num AS alembic_revision FROM alembic_version;
