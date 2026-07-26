# Cold Storage WMS — Full Production Deployment Report

This document details the step-by-step production deployment process of the Cold Storage WMS application on the remote Oracle Cloud VM (`141.148.192.136`).

---

## 1. System Architecture & Port Mapping

The VM hosts an existing ERPNext instance (occupying port `8000`), so the Cold Storage WMS is configured to run adjacent to it on port `8001`.

```
                        [ Internet Traffic ]
                                 │
                                 ▼
                     [ Cloudflare (SSL/Proxy) ]
                                 │ (HTTPS / Port 443)
                                 ▼
                         [ Nginx (Port 80) ]
       ┌─────────────────────────┼─────────────────────────┐
       ▼                         ▼                         ▼
 [ Vue Frontend ]       [ Django Gunicorn ]       [ Media Folder ]
  Served Statically       Proxied to Port 8001      Served Directly
 (frontend/dist/)         (gunicorn workers)      (cold_storage/media/)
```

---

## 2. Step-by-Step Deployment Chronology

### Step 2.1: OS Configuration & Dependencies
The host requires system-level packages for both the PostgreSQL database client and the backend document generator (WeasyPrint), which handles PDFs:
```bash
sudo apt update
sudo apt install -y postgresql-client libpq-dev \
    python3-dev build-essential cairo-dev pango-dev \
    gdk-pixbuf-dev libglib2.0-dev shared-mime-info \
    fonts-deva fonts-noto-core
```

### Step 2.2: Directory & Repository Setup
The repository was cloned into the `frappeuser` home directory:
```bash
cd /home/frappeuser
git clone https://github.com/Slydite/cold_storage.git
cd cold_storage
```

### Step 2.3: Production Environment File (`.env`)
The environment configuration was created in `/home/frappeuser/cold_storage/.env` to configure Django for production and point to the PostgreSQL instance:
```ini
DJANGO_SECRET_KEY=<REDACTED — see .env on the VM>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=cold.crystalcubes.in,141.148.192.136,localhost,127.0.0.1

POSTGRES_DB=cold_storage
POSTGRES_USER=cold_storage_user
POSTGRES_PASSWORD=<REDACTED>
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

DJANGO_CORS_ALLOWED_ORIGINS=https://cold.crystalcubes.in,http://cold.crystalcubes.in,http://141.148.192.136:5173,http://141.148.192.136,http://localhost:5173
DJANGO_CSRF_TRUSTED_ORIGINS=https://cold.crystalcubes.in,http://cold.crystalcubes.in,http://141.148.192.136:5173,http://141.148.192.136,http://localhost:5173,http://127.0.0.1:5173
DJANGO_SECURE_SSL_REDIRECT=False
DJANGO_HSTS_SECONDS=0
```

### Step 2.4: Database Provisioning (PostgreSQL)
A new database and dedicated user were created in PostgreSQL:
```sql
CREATE DATABASE cold_storage;
CREATE USER cold_storage_user WITH PASSWORD '<REDACTED>';
GRANT ALL PRIVILEGES ON DATABASE cold_storage TO cold_storage_user;
ALTER DATABASE cold_storage OWNER TO cold_storage_user;
```

### Step 2.5: Backend Setup & Python Environment (`uv`)
Python virtual environment was managed via `uv`:
1. Installed `uv` standalone.
2. Synchronized backend packages:
   ```bash
   cd ~/cold_storage/backend
   uv sync
   ```
3. Executed Django migrations under the production settings:
   ```bash
   export DJANGO_SETTINGS_MODULE=config.settings.production
   source .venv/bin/activate
   python manage.py migrate
   ```
4. Gathered static files for WhiteNoise:
   ```bash
   python manage.py collectstatic --no-input
   ```

### Step 2.6: Frontend NVM/Node & Native Compiler Resolution
Since the remote host is a **Linux ARM64** VM, compilation of the Vite/Rolldown engine failed due to incompatible node bindings.
1. Switched the shell from Node v18 to **Node v22** via NVM:
   ```bash
   source ~/.nvm/nvm.sh
   nvm install 22
   nvm use 22
   nvm alias default 22
   ```
2. Cleaned old dependencies, reinstalled `pnpm` under Node v22, and performed a fresh install to fetch the correct ARM64 Linux binary (`@rolldown/binding-linux-arm64-gnu`):
   ```bash
   cd ~/cold_storage/frontend
   rm -rf node_modules pnpm-lock.yaml
   npm install -g pnpm
   pnpm install
   ```
3. Successfully built the production frontend bundle:
   ```bash
   pnpm build
   ```

---

## 3. Persistent Process & Web Service Setup

### Step 3.1: Gunicorn Systemd Service
The backend process is managed persistently via systemd, configured with production settings and environment variables:
Create the service configuration at `/etc/systemd/system/cold-storage-backend.service`:
```ini
[Unit]
Description=Gunicorn instance to serve Cold Storage WMS Backend
After=network.target postgresql.service

[Service]
User=frappeuser
Group=frappeuser
WorkingDirectory=/home/frappeuser/cold_storage/backend
Environment="PATH=/home/frappeuser/cold_storage/backend/.venv/bin"
Environment="DJANGO_SETTINGS_MODULE=config.settings.production"
EnvironmentFile=/home/frappeuser/cold_storage/.env
ExecStart=/home/frappeuser/cold_storage/backend/.venv/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8001 --workers 3 --log-level info

[Install]
WantedBy=multi-user.target
```
Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable cold-storage-backend.service
sudo systemctl start cold-storage-backend.service
```

### Step 3.2: Nginx Web Server Configuration
Create the site block file at `/etc/nginx/conf.d/cold.crystalcubes.in.conf`:
```nginx
server {
    listen 80;
    listen [::]:80;
    server_name cold.crystalcubes.in;

    # Frontend Static Assets
    location / {
        root /home/frappeuser/cold_storage/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Backend APIs
    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Django Admin Panel
    location /admin/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Django Static Files
    location /static/ {
        alias /home/frappeuser/cold_storage/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    # User Media Files
    location /media/ {
        alias /home/frappeuser/cold_storage/media/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }
}
```
Validate syntax and reload:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

### Step 3.3: Let's Encrypt SSL
Generate the SSL/TLS certificate to secure traffic:
```bash
sudo certbot --nginx -d cold.crystalcubes.in
```

---

## 4. Database Initialization

A Django shell script was executed to initialize the database with details of the cold storage company and create the administrator user account:
```python
from apps.facilities.services import create_facility
from apps.accounts.services import create_user_account
from apps.accounts.models import Role

# Create Working Facility
create_facility(
    name="Jaipur Cold Storage Pvt. Ltd.",
    code="JCS",
    address="Mahapura, Ajmer Road, Jaipur-302019\nB-10, Chandpole Anaj Mandi, Jaipur",
    gstin="08AABCJ7564J1Z6",
    phone="94140-61877",
    factory_phone="94140-61879",
    bank_account_no="32643066962",
    bank_ifsc="SBIN0013139",
    terms_and_conditions="Goods stored are at owner's risk."
)

# Create User Account
create_user_account(
    username="anoop@crystalcubes.in",
    password="<REDACTED>",
    email="anoop@crystalcubes.in",
    role=Role.ADMIN
)
```

---

## 5. Cheat Sheet: Service Operations & Logs

Here are the commands to monitor and manage the deployment on the VM:

| Component | Operation | Command |
| :--- | :--- | :--- |
| **Backend** | Restart | `sudo systemctl restart cold-storage-backend` |
| **Backend** | View Logs | `sudo journalctl -u cold-storage-backend -f` |
| **Backend** | Check Status | `sudo systemctl status cold-storage-backend` |
| **Nginx** | Check Syntax | `sudo nginx -t` |
| **Nginx** | Reload Config | `sudo systemctl reload nginx` |
| **Nginx** | View Error Logs | `sudo tail -f /var/log/nginx/error.log` |
| **Database** | Access Shell | `sudo -u postgres psql -d cold_storage` |
