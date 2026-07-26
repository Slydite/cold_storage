#!/usr/bin/env bash
#
# Daily Postgres backup for the Cold Storage WMS -> local disk -> Google Drive (rclone).
#
# Deliberate choices:
#  * pg_dump custom format (-Fc): compressed, and restorable selectively with
#    pg_restore. Plain SQL would be bigger and all-or-nothing.
#  * The dump is VERIFIED with `pg_restore --list` before upload. An unverified
#    backup is worse than no backup, because it is trusted right up until the
#    day it is needed.
#  * Local copies are pruned aggressively (disk is shared with ERPNext); the
#    remote holds the real retention window.
#  * Uploads are per-file to a dated path rather than `rclone sync` of a
#    directory. sync would happily propagate a local deletion (or a truncated
#    dump) to the remote and destroy history.
#
set -euo pipefail

APP_DIR="${APP_DIR:-/home/frappeuser/cold_storage}"
ENV_FILE="${ENV_FILE:-$APP_DIR/.env}"
BACKUP_DIR="${BACKUP_DIR:-/home/frappeuser/backups/cold_storage}"
RCLONE_REMOTE="${RCLONE_REMOTE:-gdrive}"
RCLONE_PATH="${RCLONE_PATH:-cold_storage_backups}"
LOCAL_RETENTION_DAYS="${LOCAL_RETENTION_DAYS:-3}"
REMOTE_RETENTION_DAYS="${REMOTE_RETENTION_DAYS:-30}"

log() { echo "[$(date -Is)] $*"; }
fail() { log "ERROR: $*"; exit 1; }

[ -f "$ENV_FILE" ] || fail "env file not found: $ENV_FILE"

# The .env on this host has CRLF line endings (it was authored on Windows).
# Sourcing it directly makes bash choke on $'\r' and can leave a stray CR at the
# end of every value, which would silently corrupt the password. Parse it
# defensively instead of sourcing.
get_env() {
  local key="$1"
  sed -e 's/\r$//' "$ENV_FILE" \
    | grep -E "^${key}=" \
    | tail -n1 \
    | cut -d= -f2- \
    | sed -e 's/^"//' -e 's/"$//'
}

PGDATABASE="$(get_env POSTGRES_DB)"
PGUSER="$(get_env POSTGRES_USER)"
PGPASSWORD="$(get_env POSTGRES_PASSWORD)"
PGHOST="$(get_env POSTGRES_HOST)"
PGPORT="$(get_env POSTGRES_PORT)"
export PGPASSWORD
: "${PGHOST:=localhost}"
: "${PGPORT:=5432}"

[ -n "$PGDATABASE" ] || fail "POSTGRES_DB missing from $ENV_FILE"
[ -n "$PGUSER" ]     || fail "POSTGRES_USER missing from $ENV_FILE"
[ -n "$PGPASSWORD" ] || fail "POSTGRES_PASSWORD missing from $ENV_FILE"

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y-%m-%d_%H%M%S)"
DUMP="$BACKUP_DIR/${PGDATABASE}_${STAMP}.dump"

log "Dumping ${PGDATABASE} from ${PGHOST}:${PGPORT} -> ${DUMP}"
pg_dump --format=custom --no-owner --no-privileges \
        --host="$PGHOST" --port="$PGPORT" --username="$PGUSER" \
        --dbname="$PGDATABASE" --file="$DUMP"

# Verify before trusting it.
[ -s "$DUMP" ] || fail "dump is empty: $DUMP"
pg_restore --list "$DUMP" >/dev/null 2>&1 || fail "dump failed verification (corrupt/unreadable): $DUMP"
log "Dump verified OK ($(du -h "$DUMP" | cut -f1))"

# Upload. Dated remote folder keeps history immutable-ish and easy to browse.
REMOTE_TARGET="${RCLONE_REMOTE}:${RCLONE_PATH}/$(date +%Y)/$(date +%m)"
log "Uploading to ${REMOTE_TARGET}/"
rclone copy "$DUMP" "$REMOTE_TARGET/" --transfers=1 --retries=3 --low-level-retries=10
log "Upload complete"

# Confirm it actually landed rather than assuming rclone's exit code covers it.
if ! rclone lsf "$REMOTE_TARGET/$(basename "$DUMP")" >/dev/null 2>&1; then
  fail "post-upload verification failed: $(basename "$DUMP") not visible on remote"
fi
log "Remote copy verified present"

# Prune.
log "Pruning local dumps older than ${LOCAL_RETENTION_DAYS}d"
find "$BACKUP_DIR" -name "${PGDATABASE}_*.dump" -type f -mtime "+${LOCAL_RETENTION_DAYS}" -print -delete || true

log "Pruning remote dumps older than ${REMOTE_RETENTION_DAYS}d"
rclone delete "${RCLONE_REMOTE}:${RCLONE_PATH}" --min-age "${REMOTE_RETENTION_DAYS}d" || true
rclone rmdirs "${RCLONE_REMOTE}:${RCLONE_PATH}" --leave-root || true

log "Backup finished successfully"
