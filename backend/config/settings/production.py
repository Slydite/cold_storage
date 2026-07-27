from decouple import Csv, config
from .base import *

# Security & Core Settings
SECRET_KEY = config('DJANGO_SECRET_KEY')
DEBUG = config('DJANGO_DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('DJANGO_ALLOWED_HOSTS', default='', cast=Csv())

# Database configuration for PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB'),
        'USER': config('POSTGRES_USER'),
        'PASSWORD': config('POSTGRES_PASSWORD'),
        'HOST': config('POSTGRES_HOST', default='localhost'),
        'PORT': config('POSTGRES_PORT', default='5432'),
    }
}

# CORS & CSRF Settings
CORS_ALLOWED_ORIGINS = config('DJANGO_CORS_ALLOWED_ORIGINS', default='', cast=Csv())
CSRF_TRUSTED_ORIGINS = config('DJANGO_CSRF_TRUSTED_ORIGINS', default='', cast=Csv())
CORS_ALLOW_CREDENTIALS = True

# Security Headers & Cookie Policies
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = config('DJANGO_SECURE_SSL_REDIRECT', default=True, cast=bool)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = config('DJANGO_HSTS_SECONDS', default=31536000, cast=int)
# Both default to False deliberately. includeSubDomains forces *every*
# subdomain of this domain to HTTPS in any browser that has visited this
# site, which breaks sibling subdomains that are still http-only, and the
# effect persists for max-age even after the header is removed. preload is
# harder still to undo. Turn these on only once every subdomain is known to
# be HTTPS-only.
SECURE_HSTS_INCLUDE_SUBDOMAINS = config(
    'DJANGO_HSTS_INCLUDE_SUBDOMAINS', default=False, cast=bool
)
SECURE_HSTS_PRELOAD = config('DJANGO_HSTS_PRELOAD', default=False, cast=bool)

# Middleware - Insert WhiteNoise immediately after SecurityMiddleware
MIDDLEWARE = list(MIDDLEWARE)
if 'whitenoise.middleware.WhiteNoiseMiddleware' not in MIDDLEWARE:
    try:
        sec_idx = MIDDLEWARE.index('django.middleware.security.SecurityMiddleware')
        MIDDLEWARE.insert(sec_idx + 1, 'whitenoise.middleware.WhiteNoiseMiddleware')
    except ValueError:
        MIDDLEWARE.insert(0, 'whitenoise.middleware.WhiteNoiseMiddleware')

# Static Files Storage (WhiteNoise)
STATIC_ROOT = BASE_DIR.parent / 'staticfiles'
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Media Files Storage
MEDIA_ROOT = BASE_DIR.parent / 'media'
MEDIA_URL = '/media/'

# Production Logging (Stdout stream for systemd/Docker logs)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
