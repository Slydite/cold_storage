# Deployment Guide — Cold Storage Management System

This document outlines the deployment workflow and system dependencies for moving the Cold Storage WMS from local development to a Linux virtual machine using Docker or bare-metal environment setup.

---

## 1. System Dependencies (VM Apt Package List)

WeasyPrint requires native system libraries for layout rendering, font shaping, Cairo surface rendering, and Devanagari script support (used in Hindi receipts and terms). 

If deploying directly on a bare-metal Linux VM (Debian Bookworm / Ubuntu 22.04+), install the following apt packages:

```bash
sudo apt-get update && sudo apt-get install -y \
  libpango-1.0-0 \
  libpangoft2-1.0-0 \
  libharfbuzz0b \
  libcairo2 \
  fonts-noto-devanagari \
  fonts-noto-core
```

*(Note: These exact packages are pre-installed in `backend/Dockerfile` for containerized deployment).*

---

## 2. Environment Configuration & Deployment Sequence

### Step 1: Create Production Environment Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Generate a secure, random `DJANGO_SECRET_KEY` using Python:
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

3. Edit `.env` and fill in:
   - `DJANGO_SECRET_KEY` (output from command above)
   - `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
   - `DJANGO_ALLOWED_HOSTS`, `DJANGO_CORS_ALLOWED_ORIGINS`, `DJANGO_CSRF_TRUSTED_ORIGINS`

### Step 2: First-Run Container Sequence

1. Start the PostgreSQL database container:
   ```bash
   docker compose up -d db
   ```

2. Wait until the database passes its healthcheck (verify with `docker compose ps` until status shows `healthy`).

3. Run database migrations using production settings:
   ```bash
   docker compose run backend python manage.py migrate --settings=config.settings.production
   ```

4. Create the initial administrative user:
   ```bash
   docker compose run backend python manage.py createsuperuser --settings=config.settings.production
   ```

5. Launch all services in detached mode:
   ```bash
   docker compose up -d
   ```

---

## 3. Media Serving Architecture & Follow-Up Fix

**Current Gap:** WhiteNoise is configured to serve compressed static assets (`/static/`) from `STATIC_ROOT`. WhiteNoise intentionally does not serve user-uploaded media files (`MEDIA_ROOT` / `/media/`).

**Intended Real Fix:**
In production, serve `/media/` directly via Nginx mounted to the shared `media_data` Docker volume, or migrate file storage to an S3-compatible object store (e.g. AWS S3 or MinIO) using `django-storages`.

---

## 4. PDF Persistence Behavior

**Current Code Behavior:**
PDF documents (GRN receipts, Delivery Notes, Rent Run summaries, and GST Invoices) are rendered on demand using WeasyPrint and **persistently stored to disk** in `MEDIA_ROOT` via model `FileField.save()` calls:
- `GRN`: saved to `media/grns/<grn_number>.pdf` (`GRN.pdf_file`)
- `DeliveryNote`: saved to `media/delivery_notes/<dn_number>.pdf` (`DeliveryNote.pdf_file`)
- `RentRun`: saved to `media/rent_runs/RentRun_<id>.pdf` (`RentRun.pdf_file`)
- `Invoice`: saved to `media/invoices/<invoice_number>.pdf` (`Invoice.pdf_file`)

PDF files are persisted to disk upon generation and served back via their relative media URLs.
