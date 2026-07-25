FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.production

# Install OS runtime packages required for WeasyPrint (Pango/Cairo/HarfBuzz) & Devanagari font rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libcairo2 \
    fonts-noto-devanagari \
    fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv dependency manager
RUN pip install --no-cache-dir uv

# Copy dependency manifests and sync frozen production dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy backend source code
COPY . .

# Pre-compile static assets into STATIC_ROOT using placeholder env vars
RUN DJANGO_SECRET_KEY=build-time-placeholder-key-for-collectstatic \
    DJANGO_ALLOWED_HOSTS=* \
    POSTGRES_DB=dummy \
    POSTGRES_USER=dummy \
    POSTGRES_PASSWORD=dummy \
    python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "config.wsgi:application"]
