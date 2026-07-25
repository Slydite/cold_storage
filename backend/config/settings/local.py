from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR.parent / 'db' / 'db.sqlite3',
    }
}

# CORS settings
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]

CORS_ALLOW_CREDENTIALS = True

# The Vue dev server proxies /api to Django, so requests are same-origin and the
# session cookie applies. These cover the direct-origin case (no proxy).
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]

MEDIA_ROOT = BASE_DIR.parent / 'media'
MEDIA_URL = '/media/'

