#!/usr/bin/env bash
# REL-02 / SAD §4.2 — daily backup for self-managed PostgreSQL (managed databases: use the provider's PITR + snapshots
# instead and skip this script). Requires: pg_basebackup, WAL archiving (postgresql.conf below), an encrypted target.
#
#   postgresql.conf:  wal_level = replica
#                     archive_mode = on
#                     archive_command = 'test ! -f /backup/wal/%f && cp %p /backup/wal/%f'   # 7 days kept → PITR
#
# Retention: base backups 30 days, WAL 7 days. The backup volume is encrypted at rest (LG-11).
set -euo pipefail

BACKUP_ROOT="${BACKUP_ROOT:-/backup}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
: "${PGHOST:?}" "${PGUSER:?}"   # PGPASSWORD from the secrets manager

mkdir -p "$BACKUP_ROOT/base" "$BACKUP_ROOT/wal"
pg_basebackup --pgdata="$BACKUP_ROOT/base/$STAMP" --format=tar --gzip --wal-method=stream \
  --checkpoint=fast --label="chatdocs-$STAMP" --progress
echo "$STAMP" > "$BACKUP_ROOT/base/LATEST"

find "$BACKUP_ROOT/base" -mindepth 1 -maxdepth 1 -type d -mtime +30 -exec rm -rf {} +
find "$BACKUP_ROOT/wal" -type f -mtime +7 -delete
echo "backup $STAMP done"
