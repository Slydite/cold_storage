#!/usr/bin/env bash
#
# Encrypted backup of the things that are NOT in the database but that the VM
# cannot be rebuilt without: app secrets, service config, and the Play signing
# keystore.
#
# Deliberate choices:
#  * ENCRYPTED, unlike the database dump. Every file in here is itself a
#    credential (Postgres password, Django SECRET_KEY, Google refresh token,
#    keystore + its passwords). Uploading them as plaintext would make the
#    Google account the single thing protecting them. Encrypting with a
#    passphrase held in a password manager means a compromised Drive yields
#    ciphertext and nothing else.
#  * The passphrase lives in a 0600 file on this host so the timer can run
#    unattended. That defends against Drive compromise, not against host
#    compromise - if someone already has the box they have the secrets anyway.
#  * openssl aes-256-cbc with PBKDF2 and a high iteration count, rather than
#    rclone's crypt remote, so a restore needs nothing but openssl and the
#    passphrase - no rclone config, which may itself be part of what was lost.
#  * The keystore is matched by glob and its absence is NOT an error: it does
#    not exist until the app is first published, and this script must start
#    protecting it automatically on the day it appears rather than needing to
#    be remembered.
set -euo pipefail

APP_DIR="${APP_DIR:-/home/frappeuser/cold_storage}"
BACKUP_DIR="${BACKUP_DIR:-/home/frappeuser/backups/cold_storage_secrets}"
PASSPHRASE_FILE="${PASSPHRASE_FILE:-/home/frappeuser/.backup_passphrase}"
RCLONE_REMOTE="${RCLONE_REMOTE:-gdrive}"
RCLONE_PATH="${RCLONE_PATH:-cold_storage_backups/secrets}"
LOCAL_RETENTION_DAYS="${LOCAL_RETENTION_DAYS:-3}"
REMOTE_RETENTION_DAYS="${REMOTE_RETENTION_DAYS:-90}"

log() { echo "[$(date -Is)] $*"; }
fail() { log "ERROR: $*"; exit 1; }

[ -f "$PASSPHRASE_FILE" ] || fail "passphrase file not found: $PASSPHRASE_FILE"
[ -s "$PASSPHRASE_FILE" ] || fail "passphrase file is empty: $PASSPHRASE_FILE"

STAMP="$(date +%Y-%m-%d_%H%M%S)"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$BACKUP_DIR"

STAGE_DIR="$STAGE/secrets_${STAMP}"
mkdir -p "$STAGE_DIR"

collect() {
  local src="$1" label="$2"
  if [ -e "$src" ]; then
    cp -a "$src" "$STAGE_DIR/" 2>/dev/null && log "  + ${label}" && return 0
    log "  ! ${label} exists but could not be read (permissions?)"
    return 0
  fi
  log "  - ${label} (absent, skipped)"
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
# never be updated again, only replaced by a new app.
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

ARCHIVE="$STAGE/secrets_${STAMP}.tar.gz"
ENCRYPTED="$BACKUP_DIR/secrets_${STAMP}.tar.gz.enc"

log "Archiving $(ls -1 "$STAGE_DIR" | wc -l) item(s)"
tar -czf "$ARCHIVE" -C "$STAGE" "secrets_${STAMP}"

log "Encrypting (aes-256-cbc, pbkdf2)"
openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt \
        -in "$ARCHIVE" -out "$ENCRYPTED" -pass "file:$PASSPHRASE_FILE"
chmod 600 "$ENCRYPTED"

# Verify the ciphertext actually decrypts before trusting it. An unverified
# backup is worse than none, because it is believed right up until it is needed.
log "Verifying the encrypted archive decrypts and is a valid tarball"
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
        -in "$ENCRYPTED" -pass "file:$PASSPHRASE_FILE" \
  | tar -tzf - >/dev/null 2>&1 \
  || fail "encrypted archive failed verification - not uploading"
log "Verified OK ($(du -h "$ENCRYPTED" | cut -f1))"

REMOTE_TARGET="${RCLONE_REMOTE}:${RCLONE_PATH}/$(date +%Y)/$(date +%m)"
log "Uploading to ${REMOTE_TARGET}/"
rclone copy "$ENCRYPTED" "$REMOTE_TARGET/" --transfers=1 --retries=3 --low-level-retries=10

if ! rclone lsf "$REMOTE_TARGET/$(basename "$ENCRYPTED")" >/dev/null 2>&1; then
  fail "post-upload verification failed: $(basename "$ENCRYPTED") not visible on remote"
fi
log "Remote copy verified present"

log "Pruning local archives older than ${LOCAL_RETENTION_DAYS}d"
find "$BACKUP_DIR" -name "secrets_*.tar.gz.enc" -type f -mtime "+${LOCAL_RETENTION_DAYS}" -print -delete || true

log "Pruning remote archives older than ${REMOTE_RETENTION_DAYS}d"
rclone delete "${RCLONE_REMOTE}:${RCLONE_PATH}" --min-age "${REMOTE_RETENTION_DAYS}d" || true
rclone rmdirs "${RCLONE_REMOTE}:${RCLONE_PATH}" --leave-root || true

log "Secrets backup finished successfully"
