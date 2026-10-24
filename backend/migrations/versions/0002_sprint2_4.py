"""Sprint 2 → 4 additions: scheduled-job dedupe, purge-overdue index, Q&A lookups, audit-log privileges.

Revision ID: 0002
Revises: 0001
"""

from __future__ import annotations

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

UPGRADE = [
    # One scheduled job per slot even with several workers (application/maintenance.py, enqueue_once)
    "CREATE UNIQUE INDEX ux_job_slot ON platform.job (type, (payload->>'slot')) WHERE payload ? 'slot'",
    # SEC-06 alert: removed more than 20 h ago and not purged yet (T204.3)
    "CREATE INDEX ix_doc_purge_pending ON documents.document (removed_at) "
    "WHERE removed_at IS NOT NULL AND purged_at IS NULL",
    "CREATE INDEX ix_conversation_session ON qa.conversation (session_id)",
    "CREATE INDEX ix_citation_document ON qa.citation (document_id)",
    "CREATE INDEX ix_eval_result_run ON evaluation.result (run_id)",
    # T-EN09.4: the application role may only INSERT / SELECT the audit log (no tampering). The role is created by
    # infrastructure (IaC); the block is a no-op where it does not exist (dev, CI).
    """
    DO $$
    BEGIN
      IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_rw') THEN
        REVOKE UPDATE, DELETE, TRUNCATE ON platform.audit_log FROM app_rw;
        GRANT INSERT, SELECT ON platform.audit_log TO app_rw;
      END IF;
    END $$
    """,
]

DOWNGRADE = [
    "DROP INDEX IF EXISTS evaluation.ix_eval_result_run",
    "DROP INDEX IF EXISTS qa.ix_citation_document",
    "DROP INDEX IF EXISTS qa.ix_conversation_session",
    "DROP INDEX IF EXISTS documents.ix_doc_purge_pending",
    "DROP INDEX IF EXISTS platform.ux_job_slot",
]


def upgrade() -> None:
    for stmt in UPGRADE:
        op.execute(stmt)


def downgrade() -> None:
    for stmt in DOWNGRADE:
        op.execute(stmt)
