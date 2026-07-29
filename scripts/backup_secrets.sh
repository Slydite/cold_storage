#!/usr/bin/env bash
#
# Backup of the things that are NOT in the database but that the VM cannot be
# rebuilt without: app secrets, service config, and the Play signing keystore.
#
# Deliberate choices:
#  * STORED IN PLAINTEXT, and that is a considered decision rather than an
#    oversight. An earlier version encrypted this archive with a passphrase.
#    The owner's objection was decisive: a passphrase that has to survive four
#    years of not being needed will not survive, and a backup that cannot be
#    restored is worse than no backup at all. Availability beats
#    confidentiality here. The consequence is explicit: anyone with access to
#    the Google account holds the Postgres password, the Django SECRET_KEY,
#    the Google refresh token, and eventually the Play keystore. That account
#    must have 2FA and must not share this folder.
#  * The archive is listed with `tar -tzf` before upload, because an
#    unverified backup is trusted right up until the day it is needed.
#  * Presence on the remote is confirmed after upload rather than trusting
#    rclone's exit code alone.
#  * The keystore is matched by glob and its absence is NOT an error: it does
#    not exist until the app is first published, and this script must start
#    protecting it automatically on the day it appears rather than needing to
#    be remembered.
set -euo pipefail

APP_DIR="${APP_DIR:-/home/frappeuser/cold_storage}"
BACKUP_DIR="${BACKUP_DIR:-/home/frappeuser/backups/cold_storage_secrets}"
RCLONE_REMOTE="${RCLONE_REMOTE:-gdrive}"
RCLONE_PATH="${RCLONE_PATH:-cold_storage_backups/secrets}"
LOCAL_RETENTION_DAYS="${LOCAL_RETENTION_DAYS:-3}"
REMOTE_RETENTION_DAYS="${REMOTE_RETENTION_DAYS:-90}"

log() { echo "[$(date -Is)] $*"; }
fail() { log "ERROR: $*"; exit 1; }

STAMP="$(date +%Y-%m-%d_%H%M%S)"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$BACKUP_DIR"

STAGE_DIR="$STAGE/secrets_${STAMP}"
mkdir -p "$STAGE_DIR"

collect() {
  local src="$1" label="$2"
  if [ -e "$src" ]; then
    if cp -a "$src" "$STAGE_DIR/" 2>/dev/null; then
      log "  + ${label}"
    else
      log "  ! ${label} exists but could not be read (permissions?)"
    fi
  else
    log "  - ${label} (absent, skipped)"
  fi
}

log "Collecting secrets and config"
collect "$APP_DIR/.env"                                        ".env (Django secret key, DB password)"
collect "$HOME/.config/rclone/rclone.conf"                     "rclone.conf (Google refresh token)"
collect "/etc/nginx/conf.d/cold.crystalcubes.in.conf"          "nginx site config"
collect "/etc/systemd/system/cold-storage-backend.service"     "gunicorn systemd unit"
collect "/etc/systemd/system/cold-storage-backup.service"      "backup systemd unit"
collect "/etc/systemd/system/cold-storage-backup.timer"        "backup systemd timer"

# Play signing keystore. Does not exist until the Android app is first built
# for release. Unrecoverable if lost - losing it means the Play listing can
# never be updated again, only replaced by a new app under a new package name.
shopt -s nullglob
KEYSTORES=(
  "$APP_DIR"/frontend/android/app/*.keystore
  "$APP_DIR"/frontend/android/app/*.jks
  "$HOME"/keystores/*.keystore
  "$HOME"/keystores/*.jks
)
shopt -u nullglob
if [ ${#KEYSTORES[@]} -eq 0 ]; then
  log "  - Play signing keystore (none found yet - will be included automatically once created)"
else
  for ks in "${KEYSTORES[@]}"; do
    cp -a "$ks" "$STAGE_DIR/" && log "  + keystore $(basename "$ks")"
  done
fi

# Refuse to upload an archive containing nothing of value.
if [ -z "$(ls -A "$STAGE_DIR")" ]; then
  fail "nothing was collected - refusing to upload an empty archive"
fi

ARCHIVE="$BACKUP_DIR/secrets_${STAMP}.tar.gz"

log "Archiving $(ls -1 "$STAGE_DIR" | wc -l) item(s)"
tar -czf "$ARCHIVE" -C "$STAGE" "secrets_${STAMP}"
chmod 600 "$ARCHIVE"

# Verify before trusting it.
[ -s "$ARCHIVE" ] || fail "archive is empty: $ARCHIVE"
tar -tzf "$ARCHIVE" >/dev/null 2>&1 || fail "archive failed verification (corrupt/unreadable): $ARCHIVE"
log "Archive verified OK ($(du -h "$ARCHIVE" | cut -f1))"

REMOTE_TARGET="${RCLONE_REMOTE}:${RCLONE_PATH}/$(date +%Y)/$(date +%m)"
log "Uploading to ${REMOTE_TARGET}/"
rclone copy "$ARCHIVE" "$REMOTE_TARGET/" --transfers=1 --retries=3 --low-level-retries=10

if ! rclone lsf "$REMOTE_TARGET/$(basename "$ARCHIVE")" >/dev/null 2>&1; then
  fail "post-upload verification failed: $(basename "$ARCHIVE") not visible on remote"
fi
log "Remote copy verified present"

log "Pruning local archives older than ${LOCAL_RETENTION_DAYS}d"
find "$BACKUP_DIR" -name "secrets_*.tar.gz" -type f -mtime "+${LOCAL_RETENTION_DAYS}" -print -delete || true

log "Pruning remote archives older than ${REMOTE_RETENTION_DAYS}d"
rclone delete "${RCLONE_REMOTE}:${RCLONE_PATH}" --min-age "${REMOTE_RETENTION_DAYS}d" || true
rclone rmdirs "${RCLONE_REMOTE}:${RCLONE_PATH}" --leave-root || true

log "Secrets backup finished successfully"
