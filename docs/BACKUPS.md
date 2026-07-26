# Database backups (Postgres → Google Drive via rclone)

Daily `pg_dump` of the `cold_storage` database, uploaded to Google Drive and
pruned on a schedule. Runs as a systemd timer on the VM.

| Piece | Where |
| --- | --- |
| Backup script | `scripts/backup_db.sh` |
| systemd service | `scripts/cold-storage-backup.service` |
| systemd timer | `scripts/cold-storage-backup.timer` |
| Local dumps | `/home/frappeuser/backups/cold_storage/` (kept 3 days) |
| Remote dumps | `gdrive:cold_storage_backups/YYYY/MM/` (kept 30 days) |
| Schedule | 02:30 daily, `Persistent=true` so a missed run catches up on boot |

Retention is set by `LOCAL_RETENTION_DAYS` / `REMOTE_RETENTION_DAYS` in the
script, overridable per-host via `systemctl edit cold-storage-backup.service`.

---

## Why OAuth and not a service account

A service account cannot write to a **free personal** Google Drive: service
accounts get no My Drive storage quota of their own, and impersonating a human
account requires domain-wide delegation, which is Google Workspace only. So the
one-time interactive OAuth flow below is the correct path for a free account.

If this ever moves to a Workspace/Shared Drive, switch to a service account —
it removes the token-refresh failure mode entirely.

---

## One-time setup

### 1. Install rclone on the VM

```bash
sudo -v ; curl https://rclone.org/install.sh | sudo bash
rclone version
```

### 2. Authorise Google Drive

The VM is headless, so authorise on a machine **with a browser** and paste the
token across. On your local machine (rclone installed there too):

```bash
rclone authorize "drive"
```

A browser opens; approve access. rclone prints a JSON token blob — copy all of
it, including the braces.

Then on the VM:

```bash
rclone config
# n) New remote
# name> gdrive
# Storage> drive
# client_id>        (blank — press enter)
# client_secret>    (blank — press enter)
# scope> 1          (full access)   ... or 3 for drive.file, see note below
# service_account_file> (blank)
# Edit advanced config? n
# Use web browser to automatically authenticate? n     <-- IMPORTANT on a headless box
# config_token> <paste the JSON blob from rclone authorize>
# Configure this as a Shared Drive (Team Drive)? n
# y) Yes this is OK
```

Scope note: `drive.file` (option 3) restricts rclone to only files it created,
which is the tighter choice and sufficient here. `drive` (option 1) grants full
account access — only pick it if you hit a limitation.

Verify:

```bash
rclone lsd gdrive:
rclone mkdir gdrive:cold_storage_backups
```

### 3. Install the timer

```bash
cd /home/frappeuser/cold_storage
chmod +x scripts/backup_db.sh

sudo cp scripts/cold-storage-backup.service /etc/systemd/system/
sudo cp scripts/cold-storage-backup.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cold-storage-backup.timer
```

### 4. Prove it works — do not wait for 02:30

```bash
sudo systemctl start cold-storage-backup.service
journalctl -u cold-storage-backup -n 40 --no-pager
rclone ls gdrive:cold_storage_backups
```

The script verifies the dump with `pg_restore --list` before uploading and
confirms the file is visible on the remote afterwards, so a green run means a
genuinely restorable file actually landed — not just that `pg_dump` exited 0.

---

## Restoring

```bash
# List available backups
rclone ls gdrive:cold_storage_backups

# Pull one down
rclone copy "gdrive:cold_storage_backups/2026/07/cold_storage_2026-07-26_023000.dump" /tmp/

# Inspect its contents without restoring
pg_restore --list /tmp/cold_storage_2026-07-26_023000.dump | head

# Restore into a SCRATCH database first — never straight over production
sudo -u postgres createdb cold_storage_restore_test
pg_restore --no-owner --no-privileges \
  --dbname=cold_storage_restore_test /tmp/cold_storage_*.dump
```

Only after verifying the scratch restore should you consider replacing the live
database. Dumps are taken with `--no-owner --no-privileges`, so they restore
cleanly under a different role than they were created with.

---

## Checking on it

```bash
systemctl list-timers cold-storage-backup --no-pager   # when it next runs
systemctl status cold-storage-backup                   # last result
journalctl -u cold-storage-backup --since "7 days ago" # recent history
```

---

## Known gaps

- **Failures are silent.** A failed run logs to the journal but nobody is
  notified. Until something is watching, check `systemctl list-timers`
  occasionally, or add an `OnFailure=` unit that emails/pings you.
- **Dumps are unencrypted at rest on Drive.** They contain full business data —
  parties, GSTINs, invoices, and Django's password hashes. If that matters,
  layer an `rclone crypt` remote over the drive remote and point
  `RCLONE_REMOTE` at it; nothing else in the script changes.
- **Media is not backed up.** After the on-demand PDF change nothing is written
  to `media/` any more, so there is currently nothing there worth preserving —
  documents regenerate deterministically from the database. Revisit if genuine
  uploads are ever added.
- **The OAuth refresh token can be revoked** (password change, account security
  events, ~6 months of total inactivity). If backups start failing with auth
  errors, re-run step 2.
