#!/bin/sh
# Production restore drill (DoD §13.5, docs/31-backups-and-dr.md).
#
# Replays the latest backup into a fresh, isolated Postgres instance
# and runs the smoke check. Designed to be safe to run on a live
# host: it never touches the production database, only spins up a
# scratch container, restores into it, and tears it down.
#
# Inputs:
#   BACKUP_DIR      same as backup_db.sh — defaults to /var/orbiteus/backups
#   DRILL_LOG_FILE  appended on success; defaults to /var/log/orbiteus/restore_drill.log
#   POSTGRES_IMAGE  defaults to pgvector/pgvector:pg16
#
# Exit code:
#   0  drill passed (latest backup restores cleanly)
#   1  no backup found
#   2  restore failed
#   3  schema mismatch
#
# Usage:
#   sh scripts/restore_drill.sh
set -eu

: "${BACKUP_DIR:=/var/orbiteus/backups}"
: "${DRILL_LOG_FILE:=/var/log/orbiteus/restore_drill.log}"
: "${POSTGRES_IMAGE:=pgvector/pgvector:pg16}"

LATEST=$(ls -1t "$BACKUP_DIR"/orbiteus_*.sql.gz 2>/dev/null | head -n1 || true)
if [ -z "$LATEST" ]; then
  echo "[drill] FAIL: no backup found in $BACKUP_DIR" >&2
  exit 1
fi
echo "[drill] using latest backup: $LATEST"

START=$(date -u +"%Y%m%dT%H%M%SZ")
CONTAINER="orbiteus-restore-drill-$$"
PORT=$(awk 'BEGIN { srand(); print 30000 + int(rand() * 5000) }')

cleanup() {
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[drill] launching scratch postgres on host port $PORT"
docker run -d --rm --name "$CONTAINER" \
  -e POSTGRES_DB=orbiteus \
  -e POSTGRES_USER=orbiteus \
  -e POSTGRES_PASSWORD=drill \
  -p "$PORT:5432" \
  "$POSTGRES_IMAGE" >/dev/null

echo -n "[drill] waiting for postgres "
# `pg_isready` returns OK as soon as the socket is up — but the
# `POSTGRES_DB` initdb hook needs another beat. Loop on a real
# `psql -d orbiteus` round-trip so we know the database exists.
for _ in $(seq 1 60); do
  if docker exec "$CONTAINER" psql -U orbiteus -d orbiteus -c '\q' >/dev/null 2>&1; then
    echo "ready."
    break
  fi
  echo -n "."
  sleep 1
done

echo "[drill] restoring $LATEST"
if ! gunzip -c "$LATEST" | docker exec -i "$CONTAINER" \
       psql -U orbiteus -d orbiteus -v ON_ERROR_STOP=1 >/dev/null; then
  echo "[drill] FAIL: psql restore raised an error" >&2
  exit 2
fi

# Sanity check: the restored DB must contain at least the canonical
# `base_*` tables. A successful pg_dump of an empty DB would otherwise
# silently pass.
TABLE_COUNT=$(docker exec "$CONTAINER" psql -U orbiteus -d orbiteus -tAc \
  "SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'ir\\_%'")
if [ "${TABLE_COUNT:-0}" -lt 5 ]; then
  echo "[drill] FAIL: restored DB has only $TABLE_COUNT base engine tables (expected ≥5)" >&2
  exit 3
fi
echo "[drill] restored DB has $TABLE_COUNT base engine tables — schema looks healthy"

END=$(date -u +"%Y%m%dT%H%M%SZ")
mkdir -p "$(dirname "$DRILL_LOG_FILE")"
{
  echo "----"
  echo "drill_started:  $START"
  echo "drill_finished: $END"
  echo "backup_file:    $LATEST"
  echo "engine_table_count: $TABLE_COUNT"
  echo "result:         pass"
} >> "$DRILL_LOG_FILE"

echo "[drill] OK — log appended to $DRILL_LOG_FILE"
