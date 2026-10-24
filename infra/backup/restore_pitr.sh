#!/usr/bin/env bash
# REL-02: restore PostgreSQL to a point in time into an EMPTY data directory of a separate server (never in place).
#   ./restore_pitr.sh <base backup stamp | LATEST> "<target time, e.g. 2027-01-12 09:30:00+07>" <new data dir>
set -euo pipefail

BACKUP_ROOT="${BACKUP_ROOT:-/backup}"
STAMP="$1"; TARGET="$2"; DATA="$3"
[ "$STAMP" = "LATEST" ] && STAMP="$(cat "$BACKUP_ROOT/base/LATEST")"
[ -d "$DATA" ] && [ -n "$(ls -A "$DATA")" ] && { echo "refusing: $DATA is not empty"; exit 1; }

mkdir -p "$DATA"
tar -xzf "$BACKUP_ROOT/base/$STAMP/base.tar.gz" -C "$DATA"
tar -xzf "$BACKUP_ROOT/base/$STAMP/pg_wal.tar.gz" -C "$DATA/pg_wal"
cat >> "$DATA/postgresql.auto.conf" <<EOF
restore_command = 'cp $BACKUP_ROOT/wal/%f %p'
recovery_target_time = '$TARGET'
recovery_target_action = 'promote'
EOF
touch "$DATA/recovery.signal"
chmod 700 "$DATA"
echo "start PostgreSQL 16 on $DATA; it replays WAL up to $TARGET and promotes."
echo "then run: alembic current   (must print the head revision) and infra/backup/capture_state.sql"
